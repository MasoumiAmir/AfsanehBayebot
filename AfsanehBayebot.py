import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from datetime import datetime, timedelta

# Bot token and chat IDs
BOT_TOKEN = 'your_bot_token'  # Replace with your bot token
GROUP_CHAT_ID = 'your_group_chat_id'  # Replace with your group ID
CHANNEL_CHAT_ID = 'your_channel_chat_id'  # Replace with your channel username

# Global variables
bot_paused = False
start_time = datetime.now()
user_language = "fa"  # زبان پیشفرض فارسی

# دیکشنری ترجمه
languages = {
    "en": {
        "welcome": "✅ Bot activated!\nI forward audio messages to the channel.",
        "status": "🔄 Status: {status}\n⏳ Uptime: {uptime}",
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
            "/language - Change language"
        ),
        "language_set": "🌐 Language set to English",
        "success_forward": "✅ Forwarded!",
        "failed_forward": "❌ Failed!",
        "reply": "↩️ Reply to a message!",
    },
    "fa": {
        "welcome": "✅ ربات فعال شد!\nپیامهای صوتی به کانال فوروارد میشوند.",
        "status": "🔄 وضعیت: {status}\n⏳ مدت فعالیت: {uptime}",
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
            "/language - تغییر زبان"
        ),
        "language_set": "🌐 زبان تنظیم شد به فارسی",
        "success_forward": "✅ ارسال شد!",
        "failed_forward": "❌ خطا!",
        "reply": "↩️ روی پیام ریپلای کنید!",
    }
}

def get_text(key):
    return languages[user_language].get(key, key)

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
        group = await fetch_messages(application, GROUP_CHAT_ID)
        channel = await fetch_messages(application, CHANNEL_CHAT_ID)
        
        group_files = {m.audio.file_id for m in group if m.audio}
        channel_files = {m.audio.file_id for m in channel if m.audio}
        missing = group_files - channel_files
        
        for msg in group:
            if msg.audio and msg.audio.file_id in missing:
                await msg.forward(CHANNEL_CHAT_ID)
                await asyncio.sleep(1)
                
    except Exception as e:
        print(f"Compare error: {e}")

async def forward_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_paused:
        try:
            await update.message.forward(CHANNEL_CHAT_ID)
        except Exception as e:
            print(f"Forward error: {e}")

async def manual_forward(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        await update.reply_text(get_text("reply"))
        return
    
    try:
        target = update.message.reply_to_message
        await target.forward(CHANNEL_CHAT_ID)
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
    text = get_text("status").format(status=status, uptime=str(uptime).split('.')[0])
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
    
    # Audio handler with group filter
    audio_filter = filters.AUDIO & filters.Chat(chat_id=GROUP_CHAT_ID)
    app.add_handler(MessageHandler(audio_filter, forward_audio))
    
    # Start polling
    print("✅ Bot is running...")
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())