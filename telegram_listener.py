"""
Telegram listener module for Battery Alert Manager
Handles background Telegram message monitoring and parsing
"""

import asyncio
import logging
import re
import threading
from queue import Queue
from typing import Optional, Dict, Callable
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError

logger = logging.getLogger(__name__)


class TelegramListener:
    """
    Asynchronous Telegram message listener with background thread execution.
    Parses messages and pushes alerts to a thread-safe queue.
    """
    
    def __init__(
        self, 
        alert_queue: Queue, 
        status_callback: Optional[Callable] = None,
        otp_callback: Optional[Callable] = None,
        password_callback: Optional[Callable] = None
    ):
        """
        Initialize Telegram listener.
        
        Args:
            alert_queue: Thread-safe queue for parsed alerts
            status_callback: Optional callback for status updates
            otp_callback: Optional callback to get OTP from user
            password_callback: Optional callback to get 2FA password from user
        """
        self.alert_queue = alert_queue
        self.status_callback = status_callback
        self.otp_callback = otp_callback
        self.password_callback = password_callback
        self.client: Optional[TelegramClient] = None
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        
        # Configuration
        self.api_id: Optional[int] = None
        self.api_hash: Optional[str] = None
        self.phone: Optional[str] = None
        self.channel_username: Optional[str] = None
        
        # Session file
        self.session_name = "battery_alert_session"
    
    def configure(
        self, 
        api_id: int, 
        api_hash: str, 
        phone: str, 
        channel_username: str
    ):
        """
        Configure Telegram connection parameters.
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            phone: Phone number
            channel_username: Channel username to monitor
        """
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.channel_username = channel_username
        logger.info(f"Telegram configured for channel: {channel_username}")
    
    def _update_status(self, status: str):
        """Update status via callback if available."""
        if self.status_callback:
            try:
                self.status_callback(status)
            except Exception as e:
                logger.error(f"Error in status callback: {e}")
        logger.info(f"Telegram status: {status}")
    
    def _get_otp_from_user(self) -> Optional[str]:
        """
        Get OTP from user via callback (runs in main thread).
        
        Returns:
            OTP code or None
        """
        if self.otp_callback:
            try:
                return self.otp_callback()
            except Exception as e:
                logger.error(f"Error getting OTP from user: {e}")
                return None
        else:
            logger.error("No OTP callback configured")
            return None
    
    def _get_password_from_user(self) -> Optional[str]:
        """
        Get 2FA password from user via callback (runs in main thread).
        
        Returns:
            Password or None
        """
        if self.password_callback:
            try:
                return self.password_callback()
            except Exception as e:
                logger.error(f"Error getting password from user: {e}")
                return None
        else:
            logger.error("No password callback configured")
            return None
    
    def _parse_alert_message(self, message_text: str) -> Optional[Dict]:
        """
        Parse Telegram message to extract alert information.
        
        Expected format examples:
        - "Alert: Battery SN12345 - Low Voltage - ACTIVE"
        - "SN: ABC123, Fault: Overcurrent, Status: CLEARED"
        - "Device: XYZ789 | Type: Temperature Alert | Status: ACTIVE"
        
        Args:
            message_text: Raw message text
            
        Returns:
            Dictionary with serial_number, fault_type, status, or None
        """
        if not message_text:
            return None
        
        # Normalize message
        text = message_text.strip()
        
        # Pattern 1: "SN: XXX, Fault: YYY, Status: ZZZ"
        pattern1 = re.compile(
            r'SN:\s*(\w+).*?Fault:\s*([^,\n]+).*?Status:\s*(ACTIVE|CLEARED)',
            re.IGNORECASE | re.DOTALL
        )
        
        # Pattern 2: "Alert: Battery XXX - YYY - ZZZ"
        pattern2 = re.compile(
            r'(?:Alert|Battery).*?(\w+)\s*-\s*([^-\n]+)\s*-\s*(ACTIVE|CLEARED)',
            re.IGNORECASE
        )
        
        # Pattern 3: "Device: XXX | Type: YYY | Status: ZZZ"
        pattern3 = re.compile(
            r'Device:\s*(\w+).*?Type:\s*([^|\n]+).*?Status:\s*(ACTIVE|CLEARED)',
            re.IGNORECASE | re.DOTALL
        )
        
        # Pattern 4: Simple format "XXX YYY ACTIVE/CLEARED"
        pattern4 = re.compile(
            r'(\w+)\s+([^-|\n,]+?)\s+(ACTIVE|CLEARED)',
            re.IGNORECASE
        )
        
        # attempt to identify priority anywhere in the text
        prio_match = re.search(r'Priority\s*[:\-]?\s*(High|Mid|Low)', text, re.IGNORECASE)
        priority = prio_match.group(1).capitalize() if prio_match else 'Mid'

        for pattern in [pattern1, pattern2, pattern3, pattern4]:
            match = pattern.search(text)
            if match:
                serial_number = match.group(1).strip()
                fault_type = match.group(2).strip()
                status = match.group(3).upper()
                
                # Validate status
                if status not in ['ACTIVE', 'CLEARED']:
                    continue
                
                logger.info(
                    f"Parsed alert: SN={serial_number}, "
                    f"Fault={fault_type}, Status={status}, Priority={priority}"
                )
                
                return {
                    'serial_number': serial_number,
                    'fault_type': fault_type,
                    'status': status,
                    'priority': priority,
                    'notes': f"From Telegram: {text[:100]}"
                }
        
        logger.debug(f"Could not parse message: {text[:100]}")
        return None
    
    async def _message_handler(self, event):
        """Handle incoming Telegram messages."""
        try:
            message = event.message
            alert_data = self._parse_alert_message(message.text)
            
            if alert_data:
                self.alert_queue.put(alert_data)
                logger.info(f"Alert queued from Telegram: {alert_data['serial_number']}")
        except Exception as e:
            logger.error(f"Error handling message: {e}")
    
    async def _authenticate(self):
        """
        Authenticate with Telegram using callbacks for OTP and password.
        
        Returns:
            True if authenticated successfully
        """
        try:
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                self._update_status("Requesting verification code...")
                await self.client.send_code_request(self.phone)
                
                self._update_status("Waiting for verification code...")
                logger.info("Code sent to Telegram. Waiting for user input...")
                
                # Get OTP from user (this will block until user provides code)
                code = self._get_otp_from_user()
                
                if not code:
                    logger.error("No OTP provided by user")
                    self._update_status("Authentication cancelled - no code provided")
                    return False
                
                try:
                    # Try to sign in with the code
                    self._update_status("Verifying code...")
                    await self.client.sign_in(self.phone, code)
                    logger.info("Successfully signed in with code")
                    
                except SessionPasswordNeededError:
                    # 2FA is enabled, need password
                    logger.info("2FA detected, requesting password")
                    self._update_status("2FA enabled - waiting for password...")
                    
                    password = self._get_password_from_user()
                    
                    if not password:
                        logger.error("No password provided by user")
                        self._update_status("Authentication cancelled - no password provided")
                        return False
                    
                    self._update_status("Verifying password...")
                    await self.client.sign_in(password=password)
                    logger.info("Successfully signed in with 2FA password")
                    
                except PhoneCodeInvalidError:
                    logger.error("Invalid verification code")
                    self._update_status("Authentication failed - invalid code")
                    return False
                
                except Exception as e:
                    logger.error(f"Sign-in error: {e}")
                    self._update_status(f"Authentication failed: {str(e)}")
                    return False
            
            # Verify we're authenticated
            if await self.client.is_user_authorized():
                me = await self.client.get_me()
                logger.info(f"Authenticated as: {me.first_name} (@{me.username})")
                self._update_status(f"Authenticated as {me.first_name}")
                return True
            else:
                logger.error("Authentication verification failed")
                self._update_status("Authentication verification failed")
                return False
            
        except Exception as e:
            logger.error(f"Authentication error: {e}", exc_info=True)
            self._update_status(f"Auth error: {str(e)}")
            return False
    
    async def _run_client(self):
        """Main async loop for Telegram client."""
        try:
            self._update_status("Connecting to Telegram...")
            
            if not await self._authenticate():
                logger.error("Authentication failed, stopping client")
                return
            
            # Get channel entity
            try:
                self._update_status(f"Finding channel {self.channel_username}...")
                channel = None
                # first attempt direct resolution
                try:
                    channel = await self.client.get_entity(self.channel_username)
                except Exception as primary_exc:
                    # try adding @ prefix if missing
                    if not self.channel_username.startswith("@"):
                        try:
                            channel = await self.client.get_entity("@" + self.channel_username)
                        except Exception:
                            channel = None

                    # if still not found, attempt a search by name
                    if channel is None:
                        try:
                            from telethon.tl.functions.contacts import SearchRequest
                            search_res = await self.client(SearchRequest(self.channel_username))
                            if search_res.chats:
                                channel = search_res.chats[0]
                            elif search_res.users:
                                channel = search_res.users[0]
                        except Exception:
                            channel = None

                    # if nothing worked, re-raise original error
                    if channel is None:
                        raise primary_exc

                logger.info(f"Successfully connected to channel: {channel.title}")
                self._update_status(f"Monitoring: {channel.title}")
            except Exception as e:
                # provide guidance for the user
                msg = (
                    f"Cannot find channel '{self.channel_username}'. "
                    "Make sure you specify the exact username (without spaces) "
                    "or include the @, or use the channel ID."
                )
                logger.error(f"Error getting channel '{self.channel_username}': {e}")
                self._update_status(f"Channel error: {msg}")
                return
            
            # Register message handler
            @self.client.on(events.NewMessage(chats=channel))
            async def handler(event):
                await self._message_handler(event)
            
            self._update_status("✓ Connected - Listening for alerts")
            self.is_running = True
            logger.info("Telegram listener active and monitoring messages")
            
            # Keep client running
            await self.client.run_until_disconnected()
            
        except Exception as e:
            logger.error(f"Telegram client error: {e}", exc_info=True)
            self._update_status(f"Error: {str(e)}")
        finally:
            self.is_running = False
            self._update_status("Disconnected")
            logger.info("Telegram client stopped")
    
    def _thread_worker(self):
        """Worker function for background thread."""
        try:
            # Create new event loop for this thread
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            
            # Create Telegram client
            self.client = TelegramClient(
                self.session_name,
                self.api_id,
                self.api_hash,
                loop=self.loop
            )
            
            # Run the client
            self.loop.run_until_complete(self._run_client())
            
        except Exception as e:
            logger.error(f"Thread worker error: {e}", exc_info=True)
            self._update_status(f"Thread error: {str(e)}")
        finally:
            if self.loop and not self.loop.is_closed():
                self.loop.close()
            logger.info("Telegram thread worker stopped")
    
    def start(self) -> bool:
        """
        Start Telegram listener in background thread.
        
        Returns:
            True if started successfully
        """
        if self.is_running:
            logger.warning("Telegram listener already running")
            self._update_status("Already running")
            return False
        
        if not all([self.api_id, self.api_hash, self.phone, self.channel_username]):
            logger.error("Telegram not configured - missing required parameters")
            self._update_status("Not configured")
            return False
        
        if not self.otp_callback:
            logger.warning("No OTP callback provided - authentication may fail")
        
        try:
            self.thread = threading.Thread(
                target=self._thread_worker,
                daemon=True,
                name="TelegramListener"
            )
            self.thread.start()
            logger.info("Telegram listener thread started")
            return True
        except Exception as e:
            logger.error(f"Error starting Telegram listener: {e}", exc_info=True)
            self._update_status(f"Start error: {str(e)}")
            return False
    
    def stop(self):
        """Stop Telegram listener."""
        if self.client and self.loop:
            try:
                # Schedule disconnect in the event loop
                future = asyncio.run_coroutine_threadsafe(
                    self.client.disconnect(),
                    self.loop
                )
                # Wait for disconnect with timeout
                future.result(timeout=5)
                logger.info("Telegram disconnected successfully")
            except Exception as e:
                logger.error(f"Error stopping Telegram: {e}")
        
        self.is_running = False
        self._update_status("Stopped")
    
    def is_configured(self) -> bool:
        """Check if Telegram is configured."""
        return all([self.api_id, self.api_hash, self.phone, self.channel_username])


class TelegramAuthenticator:
    """
    Separate authenticator for initial Telegram setup.
    Used to create session before main app runs.
    """
    
    @staticmethod
    async def authenticate(api_id: int, api_hash: str, phone: str) -> bool:
        """
        Perform initial authentication to create session.
        
        Args:
            api_id: Telegram API ID
            api_hash: Telegram API hash
            phone: Phone number
            
        Returns:
            True if authentication successful
        """
        client = TelegramClient("battery_alert_session", api_id, api_hash)
        
        try:
            await client.connect()
            
            if not await client.is_user_authorized():
                await client.send_code_request(phone)
                print("Code sent to your Telegram account")
                
                code = input("Enter the code: ")
                
                try:
                    await client.sign_in(phone, code)
                except SessionPasswordNeededError:
                    password = input("Two-step verification enabled. Enter password: ")
                    await client.sign_in(password=password)
            
            me = await client.get_me()
            print(f"Authenticated as {me.first_name}")
            
            await client.disconnect()
            return True
            
        except Exception as e:
            print(f"Authentication error: {e}")
            await client.disconnect()
            return False