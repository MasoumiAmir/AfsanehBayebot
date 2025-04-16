"""
Configuration module for AfsanehBayebot
Contains all settings and constants used in the bot
"""

import logging
import os
from datetime import datetime

# Bot tokens and IDs
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'your_bot_token')  # Bot token from BotFather
GROUP_CHAT_ID = os.environ.get('GROUP_CHAT_ID', 'your_group_chat_id')  # Group ID to monitor
CHANNEL_CHAT_ID = os.environ.get('CHANNEL_CHAT_ID', 'your_channel_chat_id')  # Channel to forward to

# Default language (can be changed during runtime)
DEFAULT_LANGUAGE = "fa"

# Database configuration
DB_PATH = 'data/forwarded_files.db'
DB_TIMEOUT = 30

# Retry configuration
MAX_RETRIES = 5
RETRY_DELAY = 5  # seconds

# Health check and watchdog
WATCHDOG_INTERVAL = 60  # seconds
ACTIVITY_TIMEOUT = 300  # seconds

# Create data directory if it doesn't exist
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Logging configuration
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_LEVEL = logging.INFO
LOG_FILE = 'logs/bot_log.log'

# Create logs directory if it doesn't exist
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# Runtime variables - will be updated during execution
runtime = {
    'bot_paused': False,
    'start_time': datetime.now(),
    'last_activity': datetime.now(),
    'user_language': DEFAULT_LANGUAGE
}

# Initialize logger
def setup_logging():
    """Set up and configure logging"""
    logging.basicConfig(
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('afsaneh_bot') 