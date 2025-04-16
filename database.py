"""
Database module for AfsanehBayebot
Handles database operations for tracking forwarded files
"""

import sqlite3
from datetime import datetime
import logging
from config import DB_PATH, DB_TIMEOUT

logger = logging.getLogger('afsaneh_bot')

class Database:
    """Database manager class for the bot"""
    
    def __init__(self):
        """Initialize the database connection and tables"""
        self.initialize_db()
    
    def get_connection(self):
        """
        Get a database connection with proper settings
        
        Returns:
            sqlite3.Connection: Database connection object
        """
        try:
            conn = sqlite3.connect(DB_PATH, timeout=DB_TIMEOUT)
            conn.isolation_level = None  # Auto-commit
            return conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}")
            raise
    
    def initialize_db(self):
        """Initialize the database tables if they don't exist"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS forwarded_files (
                file_id TEXT PRIMARY KEY,
                file_name TEXT,
                performer TEXT,
                title TEXT,
                forward_date TIMESTAMP,
                message_id INTEGER
            )
            ''')
            conn.commit()
            logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}")
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    
    def save_forwarded_file(self, file_id, file_name="", performer="", title="", message_id=0):
        """
        Save a forwarded file to the database
        
        Args:
            file_id: Unique identifier for the audio file
            file_name: Name of the file
            performer: Performer of the audio
            title: Title of the audio
            message_id: Message ID in the channel
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO forwarded_files VALUES (?, ?, ?, ?, ?, ?)",
                (file_id, file_name, performer, title, datetime.now(), message_id)
            )
            conn.commit()
            logger.debug(f"File saved to database: {file_id}")
        except sqlite3.Error as e:
            logger.error(f"Error saving forwarded file: {e}")
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    
    def is_file_forwarded(self, file_id):
        """
        Check if a file has been forwarded before
        
        Args:
            file_id: The file ID to check
            
        Returns:
            bool: True if file was forwarded, False otherwise
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM forwarded_files WHERE file_id = ?", (file_id,))
            result = cursor.fetchone() is not None
            return result
        except sqlite3.Error as e:
            logger.error(f"Error checking forwarded file: {e}")
            return False  # Assume not forwarded on error
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    
    def get_forwarded_count(self):
        """
        Get the count of forwarded files
        
        Returns:
            int: Number of forwarded files
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM forwarded_files")
            count = cursor.fetchone()[0]
            return count
        except sqlite3.Error as e:
            logger.error(f"Error getting forwarded count: {e}")
            return 0
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    
    def get_last_forwarded_date(self):
        """
        Get the date of the last forwarded file
        
        Returns:
            str: Date of last forwarded file or "N/A" if none
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT forward_date FROM forwarded_files ORDER BY forward_date DESC LIMIT 1")
            result = cursor.fetchone()
            if result:
                return result[0]
            return "N/A"
        except sqlite3.Error as e:
            logger.error(f"Error getting last forwarded date: {e}")
            return "N/A"
        finally:
            if 'conn' in locals() and conn:
                conn.close()

# Create a singleton instance for use throughout the app
db = Database() 