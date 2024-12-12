import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from datetime import datetime, timedelta

# Bot token and chat IDs
BOT_TOKEN = '7499190779:AAGFElaxYp7vNTMFdVEjezC6C7Hf8GtODIw'  # Replace with your bot token
GROUP_CHAT_ID = '@Nacuman'  # Replace with your group ID
CHANNEL_CHAT_ID = '@buy_your_gun'  # Replace with your channel username

# Global variable to track bot status
bot_paused = False
start_time = datetime.now()

async def fetch_messages(application, chat_id, days=3):
    """Fetch messages from a chat for the past `days`."""
    print("[INFO] Fetching recent messages...")
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    messages = []

    try:
        updates = await application.bot.get_updates()
        for update in updates:
            if update.message and update.message.chat.id == chat_id and update.message.date > cutoff:
                messages.append(update.message)
    except Exception as e:
        print(f"[ERROR] Error fetching messages: {e}")

    return messages

async def compare_and_forward(application):
    """Compare group and channel messages and forward missing ones."""
    group_messages = await fetch_messages(application, GROUP_CHAT_ID)
    channel_messages = await fetch_messages(application, CHANNEL_CHAT_ID)

    # Extract unique identifiers (e.g., audio file IDs) from messages
    group_audio_ids = {msg.audio.file_id for msg in group_messages if msg.audio}
    channel_audio_ids = {msg.audio.file_id for msg in channel_messages if msg.audio}

    # Find audio files that are in the group but not in the channel
    missing_audio_ids = group_audio_ids - channel_audio_ids

    for msg in group_messages:
        if msg.audio and msg.audio.file_id in missing_audio_ids:
            try:
                await application.bot.forward_message(
                    chat_id=CHANNEL_CHAT_ID,
                    from_chat_id=GROUP_CHAT_ID,
                    message_id=msg.message_id
                )
                print(f"[INFO] Forwarded missing audio: {msg.audio.file_id}")
            except Exception as e:
                print(f"[ERROR] Failed to forward audio: {e}")

async def forward_new_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new audio messages and forward them to the channel."""
    global bot_paused
    if bot_paused:
        print("[INFO] Bot is paused. Skipping new audio forwarding.")
        return

    try:
        if update.message and update.message.audio:
            await context.bot.forward_message(
                chat_id=CHANNEL_CHAT_ID,
                from_chat_id=update.message.chat.id,
                message_id=update.message.message_id
            )
            print(f"[INFO] Forwarded new audio from {update.message.chat.id} to {CHANNEL_CHAT_ID}.")
    except Exception as e:
        print(f"[ERROR] Error while forwarding new audio: {e}")

async def forward_specific_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Forward a specific message in response to a reply."""
    if not update.message.reply_to_message:
        await update.message.reply_text("Please use this command in reply to a message you want to forward.")
        return

    try:
        target_message = update.message.reply_to_message
        await context.bot.forward_message(
            chat_id=CHANNEL_CHAT_ID,
            from_chat_id=target_message.chat.id,
            message_id=target_message.message_id
        )
        await update.message.reply_text("Message forwarded successfully.")
        print(f"[INFO] Forwarded message ID {target_message.message_id} from {target_message.chat.id} to {CHANNEL_CHAT_ID}.")
    except Exception as e:
        print(f"[ERROR] Error while forwarding specific message: {e}")
        await update.message.reply_text("Failed to forward the message.")

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message."""
    await update.message.reply_text(
        "Hello! I am a bot that forwards audio messages from a group to a specific channel. Let me know if you need assistance."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the bot status."""
    status = "paused" if bot_paused else "running"
    uptime = datetime.now() - start_time
    await update.message.reply_text(
        f"The bot is currently {status}.\nUptime: {uptime}"
    )

async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pause the bot."""
    global bot_paused
    bot_paused = True
    await update.message.reply_text("The bot has been paused.")

async def resume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume the bot."""
    global bot_paused
    bot_paused = False
    await update.message.reply_text("The bot has resumed forwarding messages.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a list of commands."""
    commands = (
        "/start - Start the bot\n"
        "/status - Check bot status\n"
        "/pause - Pause forwarding\n"
        "/resume - Resume forwarding\n"
        "/help - Show this help message\n"
        "/forward - Forward a specific message (use in reply)"
    )
    await update.message.reply_text(f"Here are the commands you can use:\n{commands}")

async def main():
    print("[INFO] Starting the bot...")
    application = Application.builder().token(BOT_TOKEN).build()

    # Step 1: Compare and forward messages from the past 3 days
    await compare_and_forward(application)

    # Step 2: Handle new messages in real-time
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("pause", pause))
    application.add_handler(CommandHandler("resume", resume))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("forward", forward_specific_message))

    audio_handler = MessageHandler(filters.AUDIO, forward_new_audio)
    application.add_handler(audio_handler)

    print("[INFO] Bot is running...")
    await application.run_polling()

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()  # Ensures compatibility with existing event loops

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        print("[INFO] Bot stopped manually.")
    finally:
        loop.close()
