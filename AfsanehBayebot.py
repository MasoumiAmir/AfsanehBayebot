import asyncio
import sqlite3
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from datetime import datetime, timedelta
import os

# Bot token and chat IDs
BOT_TOKEN = 'your_bot_token'  # Replace with your bot token
GROUP_CHAT_ID = 'your_group_chat_id'  # Replace with your group ID
CHANNEL_CHAT_ID = 'your_channel_chat_id'  # Replace with your channel username

# Database setup
DB_PATH = 'forwarded_files.db'

# Global variables
bot_paused = False
start_time = datetime.now()
user_language = "fa"  # زبان پیشفرض فارسی

# دیکشنری ترجمه
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
            "/stats - View forwarding stats"
        ),
        "language_set": "🌐 Language set to English",
        "success_forward": "✅ Forwarded!",
        "failed_forward": "❌ Failed!",
        "reply": "↩️ Reply to a message!",
        "stats": "📊 Total files forwarded: {count}\n📅 Last forwarded: {last_date}",
        "already_forwarded": "⚠️ Already forwarded to channel!",
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
            "/stats - آمار ارسال‌ها"
        ),
        "language_set": "🌐 زبان تنظیم شد به فارسی",
        "success_forward": "✅ ارسال شد!",
        "failed_forward": "❌ خطا!",
        "reply": "↩️ روی پیام ریپلای کنید!",
        "stats": "📊 کل فایل‌های ارسال شده: {count}\n📅 آخرین ارسال: {last_date}",
        "already_forwarded": "⚠️ قبلاً به کانال ارسال شده است!",
    }
}

def get_text(key):
    return languages[user_language].get(key, key)

# Database functions
def init_db():
    """Initialize the database if it doesn't exist"""
    conn = sqlite3.connect(DB_PATH)
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
    conn.close()

def save_forwarded_file(file_id, file_name="", performer="", title="", message_id=0):
    """Save a forwarded file to the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO forwarded_files VALUES (?, ?, ?, ?, ?, ?)",
        (file_id, file_name, performer, title, datetime.now(), message_id)
    )
    conn.commit()
    conn.close()

def is_file_forwarded(file_id):
    """Check if a file has been forwarded before"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM forwarded_files WHERE file_id = ?", (file_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def get_forwarded_count():
    """Get the count of forwarded files"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM forwarded_files")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_last_forwarded_date():
    """Get the date of the last forwarded file"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT forward_date FROM forwarded_files ORDER BY forward_date DESC LIMIT 1")
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    return "N/A"

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        user = await context.bot.get_chat_member(
            chat_id=update.effective_chat.id,
            user_id=update.effective_user.id
        )
        return user.status in ["administrator", "creator"]
    except Exception as e:
        print(f"Admin check error: {e}")
        return False

async def fetch_messages(application, chat_id, days=3):
    cutoff = datetime.now() - timedelta(days=days)
    messages = []
    try:
        async for message in application.bot.get_chat_history(chat_id=chat_id):
            if message.date < cutoff:
                break
            if message.audio:
                messages.append(message)
    except Exception as e:
        print(f"Fetch error: {e}")
    return messages

async def compare_and_forward(application):
    try:
        group_messages = await fetch_messages(application, GROUP_CHAT_ID)
        
        for msg in group_messages:
            if msg.audio and not is_file_forwarded(msg.audio.file_id):
                forward_result = await msg.forward(CHANNEL_CHAT_ID)
                if forward_result:
                    save_forwarded_file(
                        msg.audio.file_id,
                        msg.audio.file_name or "",
                        msg.audio.performer or "",
                        msg.audio.title or "",
                        forward_result.message_id
                    )
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"Compare error: {e}")

async def forward_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if bot_paused:
        return
        
    if not update.message.audio:
        return
        
    file_id = update.message.audio.file_id
    
    # Check if already forwarded
    if is_file_forwarded(file_id):
        await update.message.reply_text(get_text("already_forwarded"))
        return
        
    try:
        forward_result = await update.message.forward(CHANNEL_CHAT_ID)
        if forward_result:
            save_forwarded_file(
                file_id,
                update.message.audio.file_name or "",
                update.message.audio.performer or "",
                update.message.audio.title or "",
                forward_result.message_id
            )
            await update.message.reply_text(get_text("success_forward"))
    except Exception as e:
        print(f"Forward error: {e}")
        await update.message.reply_text(get_text("failed_forward"))

async def manual_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.reply_text(get_text("reply"))
        return
    
    target = update.message.reply_to_message
    if not target.audio:
        await update.reply_text("❌ این پیام آهنگ نیست!")
        return
        
    file_id = target.audio.file_id
    
    # Check if already forwarded
    if is_file_forwarded(file_id):
        await update.message.reply_text(get_text("already_forwarded"))
        return
    
    try:
        forward_result = await target.forward(CHANNEL_CHAT_ID)
        if forward_result:
            save_forwarded_file(
                file_id,
                target.audio.file_name or "",
                target.audio.performer or "",
                target.audio.title or "",
                forward_result.message_id
            )
        await update.reply_text(get_text("success_forward"))
    except Exception as e:
        await update.reply_text(get_text("failed_forward"))

async def change_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_language
    if not await is_admin(update, context):
        await update.reply_text(get_text("admin_only"))
        return
    
    lang = context.args[0] if context.args else None
    if lang in languages:
        user_language = lang
        await update.reply_text(get_text("language_set"))
    else:
        await update.reply_text(f"Languages: {', '.join(languages.keys())}")

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.reply_text(get_text("welcome"))

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    status = "⏸ متوقف" if bot_paused else "▶️ فعال"
    uptime = datetime.now() - start_time
    count = get_forwarded_count()
    text = get_text("status").format(
        status=status, 
        uptime=str(uptime).split('.')[0],
        count=count
    )
    await update.reply_text(text)

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.reply_text(text)

async def pause_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.reply_text(get_text("admin_only"))
        return
    
    if update.effective_chat.id != GROUP_CHAT_ID:
        await update.reply_text(get_text("group_only"))
        return
    
    global bot_paused
    bot_paused = True
    await update.reply_text(get_text("paused"))

async def resume_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.reply_text(get_text("admin_only"))
        return
    
    if update.effective_chat.id != GROUP_CHAT_ID:
        await update.reply_text(get_text("group_only"))
        return
    
    global bot_paused
    bot_paused = False
    await update.reply_text(get_text("resumed"))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.reply_text(get_text("help"))

async def main():
    # Initialize database
    init_db()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Initial sync
    await compare_and_forward(app)
    
    # Handlers
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("pause", pause_cmd))
    app.add_handler(CommandHandler("resume", resume_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("forward", manual_forward))
    app.add_handler(CommandHandler("language", change_lang))
    app.add_handler(CommandHandler("stats", stats_cmd))
    
    # Audio handler with group filter
    audio_filter = filters.AUDIO & filters.Chat(chat_id=GROUP_CHAT_ID)
    app.add_handler(MessageHandler(audio_filter, forward_audio))
    
    # Start polling
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())