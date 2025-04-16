# AfsanehBayebot

A Telegram bot designed to automatically forward audio messages from a group to a channel.

## Features

- Forward audio messages from a specific group to a channel automatically
- Track forwarded files to prevent duplicates
- Support for multiple languages (currently English and Persian)
- Admin commands for controlling the bot
- Health monitoring and automatic recovery
- Detailed statistics and status information

## Project Structure

The project follows a modular architecture for better maintenance:

- `bot.py` - Main entry point for the application
- `config.py` - Configuration and environment settings
- `database.py` - Database operations and management
- `handlers.py` - Command and message handlers
- `localization.py` - Translation and language support
- `services.py` - Core business logic
- `utils.py` - Utility functions and helpers

## Commands

- `/start` - Start the bot
- `/status` - Get the bot's current status
- `/pause` - Pause message forwarding (admin only)
- `/resume` - Resume message forwarding (admin only)
- `/forward` - Forward a specific message (reply to a message)
- `/language` - Change the bot's language (admin only)
- `/stats` - Show forwarding statistics
- `/healthcheck` - Check the bot's health status
- `/help` - Show available commands

## Setup

1. Clone the repository
2. Install dependencies: `pip install python-telegram-bot`
3. Set up environment variables or update values in `config.py`:
   - `BOT_TOKEN` - Telegram bot token from BotFather
   - `GROUP_CHAT_ID` - Group ID to monitor for audio messages
   - `CHANNEL_CHAT_ID` - Channel ID to forward messages to
4. Run the bot: `python bot.py`

## Directory Structure

```
AfsanehBayebot/
├── bot.py              # Main entry point
├── config.py           # Configuration settings
├── database.py         # Database operations
├── handlers.py         # Command & message handlers
├── localization.py     # Language support
├── services.py         # Business logic
├── utils.py            # Utility functions
├── data/               # Database files
│   └── forwarded_files.db
├── logs/               # Log files
│   └── bot_log.log
└── README.md           # This file
```
