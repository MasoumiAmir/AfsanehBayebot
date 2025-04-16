"""
Main bot module for AfsanehBayebot
Sets up the bot and starts polling for updates
"""

import asyncio
import time
import logging
import traceback
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters
)

from config import BOT_TOKEN, GROUP_CHAT_ID, GOD_USER_ID, WATCHDOG_INTERVAL, setup_logging
from handlers import CommandHandlers, MessageHandlers, ErrorHandlers, JobHandlers
from localization import get_text

# Set up logger
logger = setup_logging()

async def main():
    """Set up and run the bot"""
    app = None
    try:
        logger.info("Starting AfsanehBayebot...")
        
        # Create application
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Register error handler
        app.add_error_handler(ErrorHandlers.error_handler)
        
        # Register command handlers
        app.add_handler(CommandHandler("start", CommandHandlers.start_command))
        app.add_handler(CommandHandler("help", CommandHandlers.help_command))
        app.add_handler(CommandHandler("status", CommandHandlers.status_command))
        app.add_handler(CommandHandler("stats", CommandHandlers.stats_command))
        app.add_handler(CommandHandler("pause", CommandHandlers.pause_command))
        app.add_handler(CommandHandler("resume", CommandHandlers.resume_command))
        app.add_handler(CommandHandler("language", CommandHandlers.language_command))
        app.add_handler(CommandHandler("forward", CommandHandlers.forward_command))
        app.add_handler(CommandHandler("healthcheck", CommandHandlers.health_check_command))
        
        # Register message handlers
        audio_filter = filters.AUDIO & filters.Chat(chat_id=GROUP_CHAT_ID)
        app.add_handler(MessageHandler(audio_filter, MessageHandlers.audio_message_handler))
        
        # Set up watchdog and initial sync jobs
        app.job_queue.run_repeating(
            JobHandlers.watchdog_job,
            interval=WATCHDOG_INTERVAL,
            first=10.0
        )
        
        app.job_queue.run_once(
            JobHandlers.initial_sync_job,
            when=5.0
        )
        
        # Start the bot
        logger.info("✅ Bot is running...")
        
        # Start the bot without using run_polling
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=["message", "edited_message", "channel_post"], drop_pending_updates=True)
        
        # Send a test message to the god user
        if GOD_USER_ID:
            await app.bot.send_message(chat_id=GOD_USER_ID, text=get_text('bot_running'))
        
        # Keep the bot running
        while True:
            await asyncio.sleep(1)
        
    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")
        logger.critical(traceback.format_exc())
        return 1  # Error
    finally:
        # Ensure proper cleanup
        if app:
            await app.stop()
            await app.shutdown()

def run_with_retry():
    """Run the main program with automatic retries on failure"""
    retry_count = 0
    max_retries = 10
    
    while retry_count < max_retries:
        try:
            # Use asyncio.run which handles the event loop properly
            asyncio.run(main())
            logger.info("Bot shut down gracefully")
            break
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
            
        except Exception as e:
            retry_count += 1
            logger.critical(f"Fatal error: {e}")
            logger.critical(traceback.format_exc())
            
            if retry_count >= max_retries:
                logger.critical(f"Exceeded maximum retry attempts ({max_retries}). Giving up.")
                break
                
            wait_time = min(60, 5 * (2 ** retry_count))  # Exponential backoff, max 60 seconds
            logger.warning(f"Restarting bot in {wait_time} seconds (attempt {retry_count}/{max_retries})...")
            time.sleep(wait_time)

if __name__ == '__main__':
    run_with_retry() 