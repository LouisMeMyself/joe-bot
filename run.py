#!/usr/bin/env python3

import os

import AvaxBot
import JoeDiscordBot
import JoeTelegramBot


def main(bot_name):
    if not bot_name:
        raise ValueError(f"Unknown bot name {bot_name}")
    bot_name = bot_name.lower().strip()
    print(f"Running {bot_name}")
    if bot_name == "avax-bot":
        AvaxBot.start()
    elif bot_name == "joe-discord-bot": 
        JoeDiscordBot.start()
    elif bot_name == "joe-telegram-bot":
        JoeTelegramBot.start()
    else:
        raise ValueError(f"Unknown bot name {bot_name}")


if __name__ == "__main__":
    bot_name = os.getenv("BOT_NAME")
    main(bot_name)