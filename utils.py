"""
Utility module for AfsanehBayebot
Contains helper functions and utilities
"""

import asyncio
import logging
import traceback
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from config import runtime, MAX_RETRIES, RETRY_DELAY, GROUP_CHAT_ID

logger = logging.getLogger('afsaneh_bot')

def update_last_activity():
    """Record the timestamp of the last activity"""
    runtime['last_activity'] = datetime.now()

async def retry_telegram_operation(operation, *args, **kwargs):
    """
    Retry a Telegram API operation with exponential backoff
    
    Args:
        operation: The async function to call
        *args, **kwargs: Arguments to pass to the function
        
    Returns:
        The result of the operation, or raises the last exception after retries
    """
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            result = await operation(*args, **kwargs)
            update_last_activity()
            return result
        except Exception as e:
            retry_count += 1
            error_type = type(e).__name__
            if retry_count >= MAX_RETRIES:
                logger.error(f"Failed after {MAX_RETRIES} retries: {error_type} - {str(e)}")
                raise
            
            wait_time = RETRY_DELAY * (2 ** (retry_count - 1))  # exponential backoff
            logger.warning(f"Retry {retry_count}/{MAX_RETRIES} after {wait_time}s due to {error_type}: {str(e)}")
            await asyncio.sleep(wait_time)

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if the user is an admin
    
    Args:
        update: Update object from Telegram
        context: Context object from Telegram
        
    Returns:
        bool: True if user is admin, False otherwise
    """
    try:
        user = await retry_telegram_operation(
            context.bot.get_chat_member,
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id
        )
        return user.status in ["administrator", "creator"]
    except Exception as e:
        logger.error(f"Admin check error: {e}")
        return False

async def check_admin_and_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Check if the user is an admin and the command is used in the proper group
    
    Args:
        update: Update object from Telegram
        context: Context object from Telegram
        
    Returns:
        bool: True if conditions are met, False otherwise
    """
    from localization import get_text
    
    # Check if user is admin
    if not await is_admin(update, context):
        await retry_telegram_operation(
            update.reply_text,
            get_text("admin_only")
        )
        return False
    
    # Check if in the right group
    if str(update.effective_chat.id) != str(GROUP_CHAT_ID):
        await retry_telegram_operation(
            update.reply_text,
            get_text("group_only")
        )
        return False
    
    return True

async def reply_to_message(update: Update, text: str):
    """
    Helper to reply to a message with error handling
    
    Args:
        update: The update object
        text: Text to send in reply
    """
    try:
        await retry_telegram_operation(
            update.reply_text,
            text
        )
    except Exception as e:
        logger.error(f"Error replying to message: {e}")
        logger.error(traceback.format_exc()) 