#!/usr/bin/env python3

import sys

import AvaxBot
import JoeDiscordBot
import JoeTelegramBot


def main(bot_name):
    bot_name = bot_name.lower().strip()
    print(f"Running {bot_name}")
    if bot_name == "avax-bot":
        AvaxBot.run()
    elif bot_name == "joe-discord-bot": 
        JoeDiscordBot.run()
    elif bot_name == "joe-telegram-bot":
        JoeTelegramBot.run()
    else:
        raise ValueError(f"Unknown bot name {bot_name}")


if __name__ == "__main__":
    num_args = len(sys.argv)
    if num_args != 2:
        print(
            f"[ERROR] Expected script to be called with `python run.py <bot name>`"
        )
        sys.exit(1)
    bot_name = sys.argv[1]
    main(bot_name)