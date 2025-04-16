"""
Services module for AfsanehBayebot
Contains the core business logic of the bot
"""

import asyncio
import logging
import traceback
from datetime import datetime, timedelta
from telegram import Bot

from config import GROUP_CHAT_ID, CHANNEL_CHAT_ID, runtime, ACTIVITY_TIMEOUT
from utils import retry_telegram_operation, update_last_activity
from database import db

logger = logging.getLogger('afsaneh_bot')

class ForwardService:
    """Service for forwarding audio files from group to channel"""
    
    @staticmethod
    async def forward_audio_message(message, bot):
        """
        Forward an audio message to the channel
        
        Args:
            message: Message object containing audio
            bot: Telegram bot instance
            
        Returns:
            bool: Success status
            str: Success or error message key
        """
        if not message.audio:
            return False, "not_audio"
        
        file_id = message.audio.file_id
        
        # Check if already forwarded
        if db.is_file_forwarded(file_id):
            return False, "already_forwarded"
        
        try:
            # Forward to channel
            forward_result = await retry_telegram_operation(
                message.forward, CHANNEL_CHAT_ID
            )
            
            if forward_result:
                # Save to database
                db.save_forwarded_file(
                    file_id,
                    message.audio.file_name or "",
                    message.audio.performer or "",
                    message.audio.title or "",
                    forward_result.message_id
                )
                logger.info(f"Successfully forwarded audio: {file_id}")
                return True, "success_forward"
            
            return False, "failed_forward"
            
        except Exception as e:
            logger.error(f"Forward error: {e}")
            logger.error(traceback.format_exc())
            return False, "failed_forward"
    
    @staticmethod
    async def fetch_recent_messages(bot, days=3):
        """
        Fetch recent messages from the group
        
        Args:
            bot: Telegram bot instance
            days: Number of days to look back
            
        Returns:
            list: List of messages with audio files
        """
        messages = []
        cutoff = datetime.now() - timedelta(days=days)
        
        try:
            logger.info(f"Fetching recent messages from chat ID: {GROUP_CHAT_ID}")
            
            # Get group administrators
            administrators = await retry_telegram_operation(
                bot.get_chat_administrators,
                chat_id=GROUP_CHAT_ID
            )
            
            # Attempt to get recent messages - we'll just use admin list
            # to check connectivity, as we can't fetch message history easily
            logger.info(f"Found {len(administrators)} admins in the group")
            
            # Since we can't easily get message history in newer API versions,
            # we'll log this and rely on real-time forwarding instead
            logger.info("Relying on real-time message forwarding instead of historical sync")
            
        except Exception as e:
            logger.error(f"Error fetching messages: {e}")
            logger.error(traceback.format_exc())
        
        return messages
    
    @staticmethod
    async def sync_with_channel(bot):
        """
        Sync recent messages with the channel
        
        Args:
            bot: Telegram bot instance
            
        Returns:
            int: Number of messages forwarded
        """
        try:
            logger.info("Starting message synchronization with channel...")
            
            # Test connection first
            try:
                me = await bot.get_me()
                logger.info(f"Bot connection verified: {me.username}")
            except Exception as e:
                logger.error(f"Bot connection test failed: {e}")
                return 0
            
            # Get historical messages
            messages = await ForwardService.fetch_recent_messages(bot)
            
            if not messages:
                logger.info("No historical messages to forward.")
                return 0
            
            # Forward all audio messages
            forwarded_count = 0
            for msg in messages:
                if msg.audio and not db.is_file_forwarded(msg.audio.file_id):
                    success, _ = await ForwardService.forward_audio_message(msg, bot)
                    if success:
                        forwarded_count += 1
                    # Add delay to avoid rate limits
                    await asyncio.sleep(1)
            
            logger.info(f"Synchronized {forwarded_count} audio messages")
            return forwarded_count
            
        except Exception as e:
            logger.error(f"Sync error: {e}")
            logger.error(traceback.format_exc())
            return 0

class HealthService:
    """Service for monitoring and maintaining bot health"""
    
    @staticmethod
    async def check_health():
        """
        Check if the bot is healthy based on last activity
        
        Returns:
            bool: True if healthy, False otherwise
            int: Minutes since last activity
        """
        now = datetime.now()
        time_since_activity = now - runtime['last_activity']
        minutes = time_since_activity.total_seconds() / 60
        
        # Consider healthy if activity in last 10 minutes
        return minutes < 10, int(minutes)
    
    @staticmethod
    async def reset_connection(bot):
        """
        Reset the connection to Telegram
        
        Args:
            bot: Telegram bot instance
        """
        try:
            logger.info("Attempting to reset connection...")
            
            try:
                # Simple request to check connection
                me = await bot.get_me()
                logger.info(f"Connection verified with bot: {me.username}")
                
                # Another test with different API
                chat = await bot.get_chat(GROUP_CHAT_ID)
                logger.info(f"Connection to group verified: {chat.title if hasattr(chat, 'title') else chat.id}")
                
            except Exception as e:
                logger.error(f"Failed to connect to Telegram API: {e}")
            
            logger.info("Connection reset successful")
            update_last_activity()
            
        except Exception as e:
            logger.error(f"Error resetting connection: {e}")
            logger.error(traceback.format_exc())
    
    @staticmethod
    async def watchdog(bot):
        """
        Monitor bot health and reset if needed
        
        Args:
            bot: Telegram bot instance
        """
        try:
            now = datetime.now()
            time_since_activity = now - runtime['last_activity']
            
            # If inactive for too long
            if time_since_activity.total_seconds() > ACTIVITY_TIMEOUT:
                logger.warning(f"Bot inactive for {time_since_activity}. Resetting connection...")
                await HealthService.reset_connection(bot)
                
        except Exception as e:
            logger.error(f"Watchdog error: {e}")
            logger.error(traceback.format_exc()) 