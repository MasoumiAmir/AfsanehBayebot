"""
Localization module for AfsanehBayebot
Manages translations and languages for the bot's messages
"""

from config import runtime

# Translation dictionary for all supported languages
translations = {
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
        "not_audio": "❌ This message is not an audio file!",
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
        "not_audio": "❌ این پیام آهنگ نیست!",
    }
}

def get_text(key, **kwargs):
    """
    Get a localized text string for the current language
    
    Args:
        key: The key for the string to retrieve
        **kwargs: Format parameters to apply to the string
        
    Returns:
        The localized string, formatted with any provided parameters
    """
    lang = runtime['user_language']
    text = translations.get(lang, {}).get(key, key)
    
    if kwargs:
        return text.format(**kwargs)
    return text

def get_supported_languages():
    """Get a list of supported languages"""
    return list(translations.keys())

def set_language(lang_code):
    """
    Set the current language
    
    Args:
        lang_code: Two-letter language code
        
    Returns:
        bool: True if successful, False if language not supported
    """
    if lang_code in translations:
        runtime['user_language'] = lang_code
        return True
    return False 