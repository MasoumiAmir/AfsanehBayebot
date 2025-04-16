"""
Configuration module for AfsanehBayebot
Contains all configuration settings and environment variables
"""

import logging
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
GROUP_CHAT_ID = int(os.getenv('GROUP_CHAT_ID', 0))
CHANNEL_CHAT_ID = int(os.getenv('CHANNEL_CHAT_ID', 0))
GOD_USER_ID = int(os.getenv('GOD_USER_ID', 0))  # اضافه کردن شناسه کاربر گاد

# Database Configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/forwarded_files.db')

# Default Language
DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'en')

# Retry Configuration
MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
RETRY_DELAY = int(os.getenv('RETRY_DELAY', 5))

# Watchdog Configuration
WATCHDOG_INTERVAL = int(os.getenv('WATCHDOG_INTERVAL', 300))  # 5 minutes

# Logging Configuration
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FILE = 'logs/bot_log.log'

# Create data directory if it doesn't exist
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Runtime variables - will be updated during execution
runtime = {
    'bot_paused': False,
    'start_time': datetime.now(),
    'last_activity': datetime.now(),
    'user_language': DEFAULT_LANGUAGE
}

def setup_logging():
    """Set up logging configuration"""
    logger = logging.getLogger('AfsanehBayebot')
    logger.setLevel(getattr(logging, LOG_LEVEL))
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(console_handler)
    
    return logger 