from telethon import TelegramClient
import asyncio

api_id = 26367328
api_hash = "07a64dfd7d9527df004218031eea5fda"
phone = "+27733642729"

async def main():
    client = TelegramClient("my_session", api_id, api_hash)
    await client.start(phone=phone)   # will ask for code
    print("✅ Logged in successfully!")
    await client.disconnect()

asyncio.run(main())