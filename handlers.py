"""
Handlers module for AfsanehBayebot
Contains all command and message handlers
"""

import logging
import traceback
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes

from config import runtime, GROUP_CHAT_ID
from localization import get_text, set_language, get_supported_languages
from utils import update_last_activity, retry_telegram_operation, check_admin_and_group, reply_to_message
from database import db
from services import ForwardService, HealthService

logger = logging.getLogger('afsaneh_bot')

class CommandHandlers:
    """Handlers for bot commands"""
    
    @staticmethod
    async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /start command"""
        update_last_activity()
        await reply_to_message(update, get_text("welcome"))
    
    @staticmethod
    async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /help command"""
        update_last_activity()
        await reply_to_message(update, get_text("help"))
    
    @staticmethod
    async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /status command"""
        update_last_activity()
        
        status = "⏸ Paused" if runtime['bot_paused'] else "▶️ Active"
        uptime = datetime.now() - runtime['start_time']
        count = db.get_forwarded_count()
        
        text = get_text("status", 
            status=status, 
            uptime=str(uptime).split('.')[0],
            count=count
        )
        
        await reply_to_message(update, text)
    
    @staticmethod
    async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /stats command"""
        update_last_activity()
        
        count = db.get_forwarded_count()
        last_date = db.get_last_forwarded_date()
        
        if isinstance(last_date, str) and last_date != "N/A":
            try:
                date_obj = datetime.fromisoformat(last_date)
                last_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        text = get_text("stats", count=count, last_date=last_date)
        await reply_to_message(update, text)
    
    @staticmethod
    async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /pause command"""
        update_last_activity()
        
        if not await check_admin_and_group(update, context):
            return
        
        runtime['bot_paused'] = True
        await reply_to_message(update, get_text("paused"))
    
    @staticmethod
    async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /resume command"""
        update_last_activity()
        
        if not await check_admin_and_group(update, context):
            return
        
        runtime['bot_paused'] = False
        await reply_to_message(update, get_text("resumed"))
    
    @staticmethod
    async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /language command"""
        update_last_activity()
        
        from utils import is_admin
        if not await is_admin(update, context):
            await reply_to_message(update, get_text("admin_only"))
            return
        
        lang = context.args[0] if context.args else None
        if lang and set_language(lang):
            await reply_to_message(update, get_text("language_set"))
        else:
            langs = ", ".join(get_supported_languages())
            await reply_to_message(update, f"Languages: {langs}")
    
    @staticmethod
    async def forward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /forward command"""
        update_last_activity()
        
        if not update.message.reply_to_message:
            await reply_to_message(update, get_text("reply"))
            return
        
        target = update.message.reply_to_message
        
        success, message_key = await ForwardService.forward_audio_message(
            target, context.bot
        )
        
        await reply_to_message(update, get_text(message_key))
    
    @staticmethod
    async def health_check_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for /healthcheck command"""
        update_last_activity()
        
        is_healthy, minutes = await HealthService.check_health()
        
        if is_healthy:
            await reply_to_message(
                update,
                get_text("health_good", time=f"{minutes} minutes")
            )
        else:
            await reply_to_message(update, get_text("health_bad"))
            await HealthService.reset_connection(context.bot)

class MessageHandlers:
    """Handlers for various message types"""
    
    @staticmethod
    async def audio_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler for audio messages"""
        update_last_activity()
        
        # Skip if bot is paused
        if runtime['bot_paused']:
            return
        
        # Skip if not in target group
        if str(update.effective_chat.id) != str(GROUP_CHAT_ID):
            return
        
        success, message_key = await ForwardService.forward_audio_message(
            update.message, context.bot
        )
        
        if message_key != "not_audio" and message_key != "already_forwarded":
            await reply_to_message(update, get_text(message_key))

class ErrorHandlers:
    """Handlers for errors and exceptions"""
    
    @staticmethod
    async def error_handler(update, context):
        """Handler for all errors in the dispatcher"""
        logger.error(f"Update {update} caused error: {context.error}")
        logger.error(traceback.format_exc())
        
        try:
            update_last_activity()
            
            if update and update.effective_chat:
                await retry_telegram_operation(
                    context.bot.send_message,
                    chat_id=update.effective_chat.id,
                    text="⚠️ An error occurred. Please try again."
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")

class JobHandlers:
    """Handlers for scheduled jobs"""
    
    @staticmethod
    async def watchdog_job(context: ContextTypes.DEFAULT_TYPE):
        """Watchdog job to monitor bot health"""
        try:
            await HealthService.watchdog(context.bot)
        except Exception as e:
            logger.error(f"Error in watchdog job: {e}")
            logger.error(traceback.format_exc())
    
    @staticmethod
    async def initial_sync_job(context: ContextTypes.DEFAULT_TYPE):
        """Initial sync job to forward old messages"""
        try:
            await ForwardService.sync_with_channel(context.bot)
        except Exception as e:
            logger.error(f"Error in initial sync job: {e}")
            logger.error(traceback.format_exc()) 