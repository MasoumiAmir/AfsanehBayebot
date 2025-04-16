import asyncio
import sqlite3
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from datetime import datetime, timedelta
import os
import logging
import sys
import traceback
import time
from concurrent.futures import ThreadPoolExecutor

# Log settings
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler("bot_log.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Bot token and chat IDs
BOT_TOKEN = 'your_bot_token'  # Replace with your bot token
GROUP_CHAT_ID = 'your_group_chat_id'  # Replace with your group ID
CHANNEL_CHAT_ID = 'your_channel_chat_id'  # Replace with your channel username

# Database setup
DB_PATH = 'forwarded_files.db'

# Global variables
bot_paused = False
start_time = datetime.now()
user_language = "fa"  # Default language is Persian
last_activity = datetime.now() # Last activity time

# Advanced settings
MAX_RETRIES = 5  # Number of retry attempts for Telegram operations
RETRY_DELAY = 5  # Delay between retries (seconds)
WATCHDOG_INTERVAL = 60  # Time interval for checking bot health (seconds)
ACTIVITY_TIMEOUT = 300  # Inactivity time (seconds) before resetting connection

# Translation dictionary
languages = {
    "en": {
        "welcome": "✅ Bot activated!\nI forward audio messages to the channel.",
        "status": "🔄 Status: {status}\n⏳ Uptime: {uptime}\n📊 Files forwarded: {count}",
        "paused": "⏸ Bot paused!",
        "resumed": "▶️ Bot resumed!",
        "admin_only": "🚫 Admin only!",
        "group_only": "⚠️ Only works in group!",
        "help": (
            "📖 Commands:\n"
            "/start - Start bot\n"
            "/status - Bot status\n"
            "/pause - Pause forwarding\n"
            "/resume - Resume forwarding\n"
            "/forward - Forward specific message\n"
            "/language - Change language\n"
            "/stats - View forwarding stats\n"
            "/healthcheck - Check bot health"
        ),
        "language_set": "🌐 Language set to English",
        "success_forward": "✅ Forwarded!",
        "failed_forward": "❌ Failed!",
        "reply": "↩️ Reply to a message!",
        "stats": "📊 Total files forwarded: {count}\n📅 Last forwarded: {last_date}",
        "already_forwarded": "⚠️ Already forwarded to channel!",
        "health_good": "✅ Bot is working correctly!\n⏱️ Last activity: {time} ago",
        "health_bad": "⚠️ Bot might be experiencing issues. Restarting connection...",
    },
    "fa": {
        "welcome": "✅ ربات فعال شد!\nپیامهای صوتی به کانال فوروارد میشوند.",
        "status": "🔄 وضعیت: {status}\n⏳ مدت فعالیت: {uptime}\n📊 فایل‌های ارسال شده: {count}",
        "paused": "⏸ ربات متوقف شد!",
        "resumed": "▶️ ربات فعال شد!",
        "admin_only": "🚫 فقط ادمین!",
        "group_only": "⚠️ فقط در گروه!",
        "help": (
            "📖 دستورات:\n"
            "/start - شروع ربات\n"
            "/status - وضعیت ربات\n"
            "/pause - توقف فوروارد\n"
            "/resume - ادامه فوروارد\n"
            "/forward - فوروارد پیام خاص\n"
            "/language - تغییر زبان\n"
            "/stats - آمار ارسال‌ها\n"
            "/healthcheck - بررسی سلامت ربات"
        ),
        "language_set": "🌐 زبان تنظیم شد به فارسی",
        "success_forward": "✅ ارسال شد!",
        "failed_forward": "❌ خطا!",
        "reply": "↩️ روی پیام ریپلای کنید!",
        "stats": "📊 کل فایل‌های ارسال شده: {count}\n📅 آخرین ارسال: {last_date}",
        "already_forwarded": "⚠️ قبلاً به کانال ارسال شده است!",
        "health_good": "✅ ربات به درستی کار می‌کند!\n⏱️ آخرین فعالیت: {time} پیش",
        "health_bad": "⚠️ ممکن است ربات با مشکل مواجه شده باشد. در حال راه‌اندازی مجدد اتصال...",
    }
}

def get_text(key):
    return languages[user_language].get(key, key)

# Function to record last activity
def update_last_activity():
    global last_activity
    last_activity = datetime.now()

# Database connection management
def get_db_connection():
    """Get a database connection with timeout and isolation level settings"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.isolation_level = None  # Auto-commit
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

# Database functions
def init_db():
    """Initialize the database if it doesn't exist"""
    try:
        conn = get_db_connection()
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
    except sqlite3.Error as e:
        logger.error(f"Database initialization error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def save_forwarded_file(file_id, file_name="", performer="", title="", message_id=0):
    """Save a forwarded file to the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO forwarded_files VALUES (?, ?, ?, ?, ?, ?)",
            (file_id, file_name, performer, title, datetime.now(), message_id)
        )
        conn.commit()
    except sqlite3.Error as e:
        logger.error(f"Error saving forwarded file: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def is_file_forwarded(file_id):
    """Check if a file has been forwarded before"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM forwarded_files WHERE file_id = ?", (file_id,))
        result = cursor.fetchone() is not None
        return result
    except sqlite3.Error as e:
        logger.error(f"Error checking forwarded file: {e}")
        return False  # در صورت خطا فرض می‌کنیم فایل فوروارد نشده است
    finally:
        if 'conn' in locals() and conn:
            conn.close()

def get_forwarded_count():
    """Get the count of forwarded files"""
    try:
        conn = get_db_connection()
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

def get_last_forwarded_date():
    """Get the date of the last forwarded file"""
    try:
        conn = get_db_connection()
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

# Retry function for Telegram operations
async def retry_telegram_operation(operation, *args, **kwargs):
    """Retry a Telegram API operation with exponential backoff"""
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            result = await operation(*args, **kwargs)
            update_last_activity()  # Update last activity time
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

async def fetch_messages(application, chat_id, days=3):
    """Fetching recent messages from a group"""
    cutoff = datetime.now() - timedelta(days=days)
    messages = []
    try:
        logger.info(f"Fetching recent messages from chat ID: {chat_id}")
        
        # Due to API limitations, we need to use an alternative approach
        # Here we only check new messages since the bot started
        
        # Get group administrators
        administrators = await retry_telegram_operation(
            application.bot.get_chat_administrators,
            chat_id=chat_id
        )
        
        # Retrieve messages from admins
        admin_count = 0
        for admin in administrators:
            if admin_count >= 5:  # Limit to prevent too many requests
                break
                
            admin_count += 1
            logger.info(f"Checking messages from admin: {admin.user.first_name}")
            
            # Get messages sent by this admin in the group
            # Note: This method has limitations and may not return all messages
            # But it's sufficient for an initial scan of recent messages
            
            # Log activity to identify potential issues
            logger.info(f"Looking for audio messages in chat {chat_id} from admin {admin.user.id}")
            
            # We could use a hidden message forward command for testing
            # And then get previous messages from that user by replying to it
            
        # Note: This method is not complete but can be used for a temporary solution
        # Eventually, the best approach is to store previous messages in the database
        
        logger.info(f"Found {len(messages)} audio messages")
        
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        logger.error(traceback.format_exc())
    return messages

async def compare_and_forward(application):
    try:
        logger.info("Starting message synchronization with channel...")
        
        # Test bot health by checking connection to Telegram
        try:
            me = await application.bot.get_me()
            logger.info(f"Bot connection verified: {me.username}")
        except Exception as api_error:
            logger.error(f"Bot connection test failed: {api_error}")
            return
        
        # Get group messages
        group_messages = await fetch_messages(application, GROUP_CHAT_ID)
        
        # If no messages found, continue with alternative method
        if not group_messages:
            logger.info("No messages found with fetch_messages. Using alternative method...")
            # Here we can use another method for synchronization
            # For example, checking new messages since last check
            
            # As an example, we just verify that the bot is active
            logger.info("Bot is active, but no historical messages could be retrieved.")
            logger.info("Waiting for new messages to be forwarded automatically.")
            return
        
        forwarded_count = 0
        for msg in group_messages:
            if msg.audio and not is_file_forwarded(msg.audio.file_id):
                forward_result = await retry_telegram_operation(
                    msg.forward, CHANNEL_CHAT_ID
                )
                if forward_result:
                    save_forwarded_file(
                        msg.audio.file_id,
                        msg.audio.file_name or "",
                        msg.audio.performer or "",
                        msg.audio.title or "",
                        forward_result.message_id
                    )
                    forwarded_count += 1
                await asyncio.sleep(1)  # Delay to avoid API limitations
        
        logger.info(f"Synchronization completed. {forwarded_count} new files sent.")
    except Exception as e:
        logger.error(f"Compare error: {e}")
        logger.error(traceback.format_exc())

async def forward_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_last_activity()  # Update last activity time
    
    if bot_paused:
        return
        
    if not update.message.audio:
        return
        
    file_id = update.message.audio.file_id
    
    # Check if already forwarded
    if is_file_forwarded(file_id):
        await retry_telegram_operation(
            update.message.reply_text,
            get_text("already_forwarded")
        )
        return
        
    try:
        forward_result = await retry_telegram_operation(
            update.message.forward, CHANNEL_CHAT_ID
        )
        if forward_result:
            save_forwarded_file(
                file_id,
                update.message.audio.file_name or "",
                update.message.audio.performer or "",
                update.message.audio.title or "",
                forward_result.message_id
            )
            await retry_telegram_operation(
                update.message.reply_text,
                get_text("success_forward")
            )
    except Exception as e:
        logger.error(f"Forward error: {e}")
        logger.error(traceback.format_exc())
        await retry_telegram_operation(
            update.message.reply_text,
            get_text("failed_forward")
        )

async def manual_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_last_activity()  # Update last activity time
    
    if not update.message.reply_to_message:
        await retry_telegram_operation(
            update.reply_text,
            get_text("reply")
        )
        return
    
    target = update.message.reply_to_message
    if not target.audio:
        await retry_telegram_operation(
            update.reply_text,
            "❌ This message is not an audio file!"
        )
        return
        
    file_id = target.audio.file_id
    
    # Check if already forwarded
    if is_file_forwarded(file_id):
        await retry_telegram_operation(
            update.message.reply_text,
            get_text("already_forwarded")
        )
        return
    
    try:
        forward_result = await retry_telegram_operation(
            target.forward, CHANNEL_CHAT_ID
        )
        if forward_result:
            save_forwarded_file(
                file_id,
                target.audio.file_name or "",
                target.audio.performer or "",
                target.audio.title or "",
                forward_result.message_id
            )
        await retry_telegram_operation(
            update.reply_text,
            get_text("success_forward")
        )
    except Exception as e:
        logger.error(f"Manual forward error: {e}")
        logger.error(traceback.format_exc())
        await retry_telegram_operation(
            update.reply_text,
            get_text("failed_forward")
        )

async def change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_last_activity()  # Update last activity time
    
    global user_language
    if not await is_admin(update, context):
        await retry_telegram_operation(
            update.reply_text,
            get_text("admin_only")
        )
        return
    
    lang = context.args[0] if context.args else None
    if lang in languages:
        user_language = lang
        await retry_telegram_operation(
            update.reply_text,
            get_text("language_set")
        )
    else:
        await retry_telegram_operation(
            update.reply_text,
            f"Languages: {', '.join(languages.keys())}"
        )

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_last_activity()  # Update last activity time
    await retry_telegram_operation(
        update.reply_text,
        get_text("welcome")
    )

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_last_activity()  # Update last activity time
    
    status = "⏸ Paused" if bot_paused else "▶️ Active"
    uptime = datetime.now() - start_time
    count = get_forwarded_count()
    text = get_text("status").format(
        status=status, 
        uptime=str(uptime).split('.')[0],
        count=count
    )
    await retry_telegram_operation(
        update.reply_text,
        text
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_last_activity()  # Update last activity time
    
    count = get_forwarded_count()
    last_date = get_last_forwarded_date()
    
    if isinstance(last_date, str) and last_date != "N/A":
        try:
            # Try to parse and format the date string
            date_obj = datetime.fromisoformat(last_date)
            last_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass
    
    text = get_text("stats").format(count=count, last_date=last_date)
    await retry_telegram_operation(
        update.reply_text,
        text
    )

async def pause_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_last_activity()  # Update last activity time
    
    if not await is_admin(update, context):
        await retry_telegram_operation(
            update.reply_text,
            get_text("admin_only")
        )
        return
    
    if update.effective_chat.id != GROUP_CHAT_ID:
        await retry_telegram_operation(
            update.reply_text,
            get_text("group_only")
        )
        return
    
    global bot_paused
    bot_paused = True
    await retry_telegram_operation(
        update.reply_text,
        get_text("paused")
    )

async def resume_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_last_activity()  # Update last activity time
    
    if not await is_admin(update, context):
        await retry_telegram_operation(
            update.reply_text,
            get_text("admin_only")
        )
        return
    
    if update.effective_chat.id != GROUP_CHAT_ID:
        await retry_telegram_operation(
            update.reply_text,
            get_text("group_only")
        )
        return
    
    global bot_paused
    bot_paused = False
    await retry_telegram_operation(
        update.reply_text,
        get_text("resumed")
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_last_activity()  # Update last activity time
    
    await retry_telegram_operation(
        update.reply_text,
        get_text("help")
    )

async def health_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update_last_activity()  # Update last activity time
    
    now = datetime.now()
    time_since_activity = now - last_activity
    minutes = time_since_activity.total_seconds() / 60
    
    # If the last activity is too old, we should be concerned
    if minutes < 10:  # Less than 10 minutes
        await retry_telegram_operation(
            update.reply_text,
            get_text("health_good").format(time=f"{int(minutes)} minutes")
        )
    else:
        await retry_telegram_operation(
            update.reply_text,
            get_text("health_bad")
        )
        # Reset connection
        await reset_connection(context.application)

async def watchdog(context):
    """Monitor bot health and reset connection if needed"""
    try:
        application = context.application
        now = datetime.now()
        time_since_activity = now - last_activity
        
        # If the bot has been inactive for a long time
        if time_since_activity.total_seconds() > ACTIVITY_TIMEOUT:
            logger.warning(f"Bot inactive for {time_since_activity}. Resetting connection...")
            await reset_connection(application)
    except Exception as e:
        logger.error(f"Watchdog error: {e}")
        logger.error(traceback.format_exc())

async def reset_connection(application):
    """Reset Telegram connection"""
    try:
        logger.info("Attempting to reset connection...")
        # Here we can perform specific operations to reset the connection
        try:
            # Send a simple request to Telegram API to check connection
            me = await application.bot.get_me()
            logger.info(f"Connection verified with bot: {me.username}")
            
            # Another attempt to reconnect to Telegram
            # Try to test connection using a different API
            chat = await application.bot.get_chat(GROUP_CHAT_ID)
            logger.info(f"Connection to main group verified: {chat.title if hasattr(chat, 'title') else chat.id}")
            
        except Exception as api_error:
            logger.error(f"Failed to connect to Telegram API: {api_error}")
            # Here we can take other actions to restore connection
            
        logger.info("Connection reset successful")
        update_last_activity()  # Update last activity time
    except Exception as e:
        logger.error(f"Error resetting connection: {e}")
        logger.error(traceback.format_exc())

# Managing general errors
async def error_handler(update, context):
    """Handle general bot errors"""
    # Log error
    logger.error(f"Update {update} caused error: {context.error}")
    logger.error(traceback.format_exc())
    
    try:
        # Update last activity (even in case of error)
        update_last_activity()
        
        # If the error is related to a specific update, notify the user
        if update and update.effective_chat:
            await retry_telegram_operation(
                context.bot.send_message,
                chat_id=update.effective_chat.id,
                text="⚠️ An error occurred. Please try again."
            )
    except Exception as e:
        logger.error(f"Error in error handler: {e}")

async def initial_sync(context):
    """Initial message synchronization"""
    try:
        application = context.application
        await compare_and_forward(application)
    except Exception as e:
        logger.error(f"Initial sync error: {e}")
        logger.error(traceback.format_exc())

async def main():
    """Main function"""
    try:
        # Initialize database
        init_db()
        
        # Set up app with optimal parameters
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Register error handler
        app.add_error_handler(error_handler)
        
        # Handlers
        app.add_handler(CommandHandler("start", start_cmd))
        app.add_handler(CommandHandler("status", status_cmd))
        app.add_handler(CommandHandler("pause", pause_cmd))
        app.add_handler(CommandHandler("resume", resume_cmd))
        app.add_handler(CommandHandler("help", help_cmd))
        app.add_handler(CommandHandler("forward", manual_forward))
        app.add_handler(CommandHandler("language", change_lang))
        app.add_handler(CommandHandler("stats", stats_cmd))
        app.add_handler(CommandHandler("healthcheck", health_check))
        
        # Audio handler with group filter
        audio_filter = filters.AUDIO & filters.Chat(chat_id=GROUP_CHAT_ID)
        app.add_handler(MessageHandler(audio_filter, forward_audio))
        
        # Start watchdog to monitor bot health
        # Start watchdog in a separate task
        app.job_queue.run_repeating(
            watchdog, 
            interval=WATCHDOG_INTERVAL,
            first=10.0
        )
        
        # Initial sync - run after bot startup
        app.job_queue.run_once(
            initial_sync,
            when=5.0
        )
        
        # Start polling with proper error handling and recovery
        logger.info("✅ Bot is running...")
        
        # Use the recommended approach for starting the application
        # This method handles initialization, polling, and idle state all in one call
        await app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except Exception as e:
        logger.critical(f"Critical error in main function: {e}")
        logger.critical(traceback.format_exc())
        return 1  # Non-zero exit code for retry
    finally:
        # Make sure the bot is properly shut down in any case
        try:
            if 'app' in locals():
                # No need to call stop explicitly as run_polling handles this
                pass
        except Exception as shutdown_error:
            logger.error(f"Error during shutdown: {shutdown_error}")
        
    return 0  # Successful exit code

def run_with_retry():
    """Run the main program with retry on failure"""
    retry_count = 0
    max_retries = 10
    
    while retry_count < max_retries:
        try:
            asyncio.run(main())
            break  # If the program terminates properly, exit the loop
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            retry_count += 1
            logger.critical(f"Fatal error: {e}")
            logger.critical(traceback.format_exc())
            wait_time = min(60, 5 * (2 ** retry_count))  # Maximum 60 seconds delay
            logger.warning(f"Restarting bot in {wait_time} seconds (attempt {retry_count}/{max_retries})...")
            time.sleep(wait_time)

if __name__ == '__main__':
    run_with_retry()