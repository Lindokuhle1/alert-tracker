"""
Database module for Battery Alert Manager
Handles SQLite database operations with thread-safe connection management
"""

import sqlite3
import threading
import logging
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Thread-safe database manager for Battery Alert Manager.
    Uses connection pooling and context managers for safe database operations.
    """
    
    def __init__(self, db_path: str = "battery_alerts.db"):
        """
        Initialize database manager.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        self._initialize_database()
        logger.info(f"Database initialized at {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """
        Get thread-local database connection.
        
        Returns:
            SQLite connection object for current thread
        """
        if not hasattr(self._local, 'connection'):
            self._local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0
            )
            self._local.connection.row_factory = sqlite3.Row
        return self._local.connection
    
    @contextmanager
    def get_cursor(self):
        """
        Context manager for database cursor with automatic commit/rollback.
        
        Yields:
            SQLite cursor object
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()
    
    def _initialize_database(self):
        """Create database tables and indexes if they don't exist."""
        with self._lock:
            with self.get_cursor() as cursor:
                # Create Devices table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS Devices (
                        DeviceId INTEGER PRIMARY KEY AUTOINCREMENT,
                        SerialNumber TEXT NOT NULL UNIQUE,
                        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create FaultTypes table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS FaultTypes (
                        FaultTypeId INTEGER PRIMARY KEY AUTOINCREMENT,
                        FaultName TEXT NOT NULL UNIQUE,
                        CreatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                
                # Create Alerts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS Alerts (
                        AlertId INTEGER PRIMARY KEY AUTOINCREMENT,
                        DeviceId INTEGER NOT NULL,
                        FaultTypeId INTEGER NOT NULL,
                        Status TEXT NOT NULL CHECK(Status IN ('ACTIVE', 'CLEARED')),
                        OccurredAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ReOccurrenceCount INTEGER DEFAULT 1,
                        Notes TEXT,
                        Priority TEXT DEFAULT 'Mid',
                        IsArchived INTEGER DEFAULT 0,
                        Resolution TEXT,
                        ArchivedAt TIMESTAMP,
                        FOREIGN KEY (DeviceId) REFERENCES Devices(DeviceId),
                        FOREIGN KEY (FaultTypeId) REFERENCES FaultTypes(FaultTypeId)
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_device 
                    ON Alerts(DeviceId)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_fault 
                    ON Alerts(FaultTypeId)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_status 
                    ON Alerts(Status)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_archived 
                    ON Alerts(IsArchived)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_alerts_critical 
                    ON Alerts(Status, ReOccurrenceCount)
                """)
                
                # Add IsCritical column if it doesn't exist
                cursor.execute("PRAGMA table_info(Alerts)")
                columns = [col[1] for col in cursor.fetchall()]
                # Add new columns if they don't exist
                if 'IsCritical' not in columns:
                    cursor.execute("""
                        ALTER TABLE Alerts 
                        ADD COLUMN IsCritical INTEGER DEFAULT 0
                    """)
                    logger.info("Added IsCritical column to Alerts table")
                    columns.append('IsCritical')

                if 'Priority' not in columns:
                    # NOTE: SQLite does not enforce CHECK on ALTER TABLE ADD
                    # so we simply add the column with default Mid.  Any
                    # validation of allowed values is done in application code.
                    cursor.execute("""
                        ALTER TABLE Alerts
                        ADD COLUMN Priority TEXT DEFAULT 'Mid'
                    """)
                    logger.info("Added Priority column to Alerts table")
                
                logger.info("Database schema initialized successfully")
    
    def get_or_create_device(self, serial_number: str) -> int:
        """
        Get device ID by serial number, create if doesn't exist.
        
        Args:
            serial_number: Device serial number
            
        Returns:
            Device ID
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT DeviceId FROM Devices WHERE SerialNumber = ?",
                (serial_number,)
            )
            result = cursor.fetchone()
            
            if result:
                return result['DeviceId']
            
            cursor.execute(
                "INSERT INTO Devices (SerialNumber) VALUES (?)",
                (serial_number,)
            )
            return cursor.lastrowid
    
    def get_or_create_fault_type(self, fault_name: str) -> int:
        """
        Get fault type ID by name, create if doesn't exist.
        
        Args:
            fault_name: Fault type name
            
        Returns:
            Fault type ID
        """
        with self.get_cursor() as cursor:
            cursor.execute(
                "SELECT FaultTypeId FROM FaultTypes WHERE FaultName = ?",
                (fault_name,)
            )
            result = cursor.fetchone()
            
            if result:
                return result['FaultTypeId']
            
            cursor.execute(
                "INSERT INTO FaultTypes (FaultName) VALUES (?)",
                (fault_name,)
            )
            return cursor.lastrowid

    
    def add_or_update_alert(
        self, 
        serial_number: str, 
        fault_name: str, 
        status: str,
        notes: Optional[str] = None,
        priority: str = "Mid"
    ) -> Tuple[int, bool]:
        """
        Add new alert or update existing one.
        If same SerialNumber + FaultType exists and is not archived,
        increment ReOccurrenceCount instead of creating new row.

        Args:
            serial_number: Device serial number
            fault_name: Fault type name
            status: Alert status (ACTIVE or CLEARED)
            notes: Optional notes
            priority: Priority level (High/Mid/Low)

        Returns:
            Tuple of (AlertId, was_updated)
        """
        """
        Add new alert or update existing one.
        If same SerialNumber + FaultType exists and is not archived,
        increment ReOccurrenceCount instead of creating new row.
        
        Args:
            serial_number: Device serial number
            fault_name: Fault type name
            status: Alert status (ACTIVE or CLEARED)
            notes: Optional notes
            
        Returns:
            Tuple of (AlertId, was_updated)
        """
        # normalize/validate priority
        if priority not in ('High', 'Mid', 'Low'):
            logger.warning(f"Invalid priority '{priority}' received, defaulting to 'Mid'")
            priority = 'Mid'

        with self._lock:
            device_id = self.get_or_create_device(serial_number)
            fault_type_id = self.get_or_create_fault_type(fault_name)
            
            with self.get_cursor() as cursor:
                # Check for existing non-archived alert with same serial+fault
                cursor.execute("""
                    SELECT AlertId, ReOccurrenceCount 
                    FROM Alerts 
                    WHERE DeviceId = ? 
                    AND FaultTypeId = ? 
                    AND IsArchived = 0
                """, (device_id, fault_type_id))
                
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing alert - prevents duplicates
                    alert_id = existing['AlertId']
                    new_count = existing['ReOccurrenceCount'] + 1
                    
                    update_query = """
                        UPDATE Alerts 
                        SET Status = ?, 
                            ReOccurrenceCount = ?,
                            OccurredAt = CURRENT_TIMESTAMP
                    """
                    params = [status, new_count]
                    
                    # include priority update as well
                    update_query += ", Priority = ?"
                    params.append(priority)

                    if notes:
                        update_query += ", Notes = ?"
                        params.append(notes)
                    
                    update_query += " WHERE AlertId = ?"
                    params.append(alert_id)
                    
                    cursor.execute(update_query, params)
                    
                    logger.info(
                        f"Updated alert {alert_id}: {serial_number} - {fault_name} "
                        f"(Count: {new_count}, Priority: {priority})"
                    )
                    return alert_id, True
                else:
                    # No active alert found.  Check if there is an archived
                    # record for the same serial/fault combination.  If so,
                    # reuse it instead of inserting a brand new row.  This
                    # ensures we never create duplicates and preserve the
                    # historical ReOccurrenceCount even across archives.
                    cursor.execute("""
                        SELECT AlertId, ReOccurrenceCount
                        FROM Alerts
                        WHERE DeviceId = ?
                        AND FaultTypeId = ?
                        AND IsArchived = 1
                    """, (device_id, fault_type_id))

                    archived = cursor.fetchone()
                    if archived:
                        alert_id = archived['AlertId']
                        new_count = archived['ReOccurrenceCount'] + 1

                        # Unarchive and update fields
                        update_query = """
                            UPDATE Alerts
                            SET Status = ?,
                                ReOccurrenceCount = ?,
                                OccurredAt = CURRENT_TIMESTAMP,
                                Priority = ?,
                                IsArchived = 0,
                                Resolution = NULL,
                                ArchivedAt = NULL
                        """
                        params = [status, new_count, priority]
                        if notes:
                            update_query += ", Notes = ?"
                            params.append(notes)
                        update_query += " WHERE AlertId = ?"
                        params.append(alert_id)

                        cursor.execute(update_query, params)
                        logger.info(
                            f"Reactivated archived alert {alert_id}: {serial_number} - {fault_name} "
                            f"(Count: {new_count})"
                        )
                        return alert_id, True

                    # Otherwise no duplicate anywhere, insert new alert
                    cursor.execute("""
                        INSERT INTO Alerts 
                        (DeviceId, FaultTypeId, Status, Notes, Priority, ReOccurrenceCount)
                        VALUES (?, ?, ?, ?, ?, 1)
                    """, (device_id, fault_type_id, status, notes, priority))
                    
                    alert_id = cursor.lastrowid
                    logger.info(
                        f"Created new alert {alert_id}: {serial_number} - {fault_name}"
                    )
                    return alert_id, False
    
    def get_all_alerts(self, include_archived: bool = False) -> List[Dict]:
        """
        Get all alerts with device and fault type information.
        
        Args:
            include_archived: Whether to include archived alerts
            
        Returns:
            List of alert dictionaries
        """
        with self.get_cursor() as cursor:
            query = """
                SELECT 
                    a.AlertId,
                    d.SerialNumber,
                    f.FaultName,
                    a.Status,
                    a.OccurredAt,
                    a.ReOccurrenceCount,
                    a.Notes,
                    a.Priority,
                    a.IsArchived,
                    a.Resolution,
                    a.ArchivedAt,
                    a.IsCritical
                FROM Alerts a
                JOIN Devices d ON a.DeviceId = d.DeviceId
                JOIN FaultTypes f ON a.FaultTypeId = f.FaultTypeId
            """
            
            if not include_archived:
                query += " WHERE a.IsArchived = 0"
            
            query += " ORDER BY a.OccurredAt DESC"
            
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_critical_alerts(self) -> List[Dict]:
        """
        Get critical alerts (ACTIVE with ReOccurrenceCount >= 5 OR manually marked as critical).
        
        Returns:
            List of critical alert dictionaries
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.AlertId,
                    d.SerialNumber,
                    f.FaultName,
                    a.Status,
                    a.OccurredAt,
                    a.ReOccurrenceCount,
                    a.Notes,
                    a.Priority,
                    a.IsArchived,
                    a.Resolution,
                    a.IsCritical
                FROM Alerts a
                JOIN Devices d ON a.DeviceId = d.DeviceId
                JOIN FaultTypes f ON a.FaultTypeId = f.FaultTypeId
                WHERE a.IsArchived = 0
                AND (
                    (a.Status = 'ACTIVE' AND a.ReOccurrenceCount >= 5)
                    OR a.IsCritical = 1
                )
                ORDER BY a.IsCritical DESC, a.ReOccurrenceCount DESC, a.OccurredAt DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_archived_alerts(self) -> List[Dict]:
        """
        Get archived alerts with resolution information.
        
        Returns:
            List of archived alert dictionaries
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.AlertId,
                    d.SerialNumber,
                    f.FaultName,
                    a.Status,
                    a.OccurredAt,
                    a.ReOccurrenceCount,
                    a.Notes,
                    a.Priority,
                    a.IsArchived,
                    a.Resolution,
                    a.ArchivedAt,
                    a.IsCritical
                FROM Alerts a
                JOIN Devices d ON a.DeviceId = d.DeviceId
                JOIN FaultTypes f ON a.FaultTypeId = f.FaultTypeId
                WHERE a.IsArchived = 1
                ORDER BY a.ArchivedAt DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
    
    def update_alert_notes(self, alert_id: int, notes: str, priority: Optional[str] = None):
        """
        Update notes (and optionally priority) for an alert.
        
        Args:
            alert_id: Alert ID
            notes: New notes text
            priority: Optional priority to set ('High','Mid','Low')
        """
        with self.get_cursor() as cursor:
            if priority and priority in ('High', 'Mid', 'Low'):
                cursor.execute(
                    "UPDATE Alerts SET Notes = ?, Priority = ? WHERE AlertId = ?",
                    (notes, priority, alert_id)
                )
                logger.info(f"Updated notes and priority for alert {alert_id}")
            else:
                cursor.execute(
                    "UPDATE Alerts SET Notes = ? WHERE AlertId = ?",
                    (notes, alert_id)
                )
                logger.info(f"Updated notes for alert {alert_id}")
    
    def update_alert_priority(self, alert_id: int, priority: str):
        """
        Set the priority of an alert.
        
        Args:
            alert_id: Alert ID
            priority: New priority ('High','Mid','Low')
        """
        if priority not in ('High', 'Mid', 'Low'):
            logger.warning(f"Attempted to set invalid priority '{priority}'")
            return
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE Alerts SET Priority = ? WHERE AlertId = ?",
                (priority, alert_id)
            )
            logger.info(f"Updated priority for alert {alert_id} to {priority}")

    def update_alert_status(self, alert_id: int, status: str):
        """
        Change the status of an alert.  Does not modify re-occurrence count.

        Args:
            alert_id: Alert ID
            status: New status ('ACTIVE' or 'CLEARED')
        """
        if status not in ('ACTIVE', 'CLEARED'):
            logger.warning(f"Attempted to set invalid status '{status}'")
            return
        with self.get_cursor() as cursor:
            cursor.execute(
                "UPDATE Alerts SET Status = ?, OccurredAt = CURRENT_TIMESTAMP WHERE AlertId = ?",
                (status, alert_id)
            )
            logger.info(f"Updated status for alert {alert_id} to {status}")
    
    def archive_alert(self, alert_id: int, resolution: str):
        """
        Archive an alert with resolution.
        
        Args:
            alert_id: Alert ID
            resolution: Resolution description
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE Alerts 
                SET IsArchived = 1, 
                    Resolution = ?,
                    ArchivedAt = CURRENT_TIMESTAMP
                WHERE AlertId = ?
            """, (resolution, alert_id))
            logger.info(f"Archived alert {alert_id}")
    
    def unarchive_alert(self, alert_id: int):
        """
        Unarchive an alert.
        
        Args:
            alert_id: Alert ID
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE Alerts 
                SET IsArchived = 0, 
                    Resolution = NULL,
                    ArchivedAt = NULL
                WHERE AlertId = ?
            """, (alert_id,))
            logger.info(f"Unarchived alert {alert_id}")
    
    def mark_as_critical(self, alert_id: int):
        """
        Manually mark an alert as critical.
        
        Args:
            alert_id: Alert ID
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE Alerts 
                SET IsCritical = 1
                WHERE AlertId = ?
            """, (alert_id,))
            logger.info(f"Marked alert {alert_id} as critical")
    
    def unmark_as_critical(self, alert_id: int):
        """
        Remove critical marking from an alert.
        
        Args:
            alert_id: Alert ID
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                UPDATE Alerts 
                SET IsCritical = 0
                WHERE AlertId = ?
            """, (alert_id,))
            logger.info(f"Unmarked alert {alert_id} as critical")
    
    def get_alert_by_id(self, alert_id: int) -> Optional[Dict]:
        """
        Get single alert by ID.
        
        Args:
            alert_id: Alert ID
            
        Returns:
            Alert dictionary or None
        """
        with self.get_cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.AlertId,
                    d.SerialNumber,
                    f.FaultName,
                    a.Status,
                    a.OccurredAt,
                    a.ReOccurrenceCount,
                    a.Notes,
                    a.IsArchived,
                    a.Resolution,
                    a.ArchivedAt,
                    a.IsCritical
                FROM Alerts a
                JOIN Devices d ON a.DeviceId = d.DeviceId
                JOIN FaultTypes f ON a.FaultTypeId = f.FaultTypeId
                WHERE a.AlertId = ?
            """, (alert_id,))
            
            result = cursor.fetchone()
            return dict(result) if result else None
    
    def close(self):
        """Close database connections."""
        if hasattr(self._local, 'connection'):
            self._local.connection.close()
            logger.info("Database connection closed")
