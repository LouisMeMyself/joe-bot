import os

import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv

from joeBot import JoeSubGraph

load_dotenv()

# Discord
discord_bot = commands.Bot(command_prefix='./.')


class AvaxTicker(commands.Cog):
    def __init__(self):
        self.carousel = True

    def start(self):
        self.ticker.start()

    def stop(self):
        print("Stopping {}".format(type(self).__name__))
        self.ticker.cancel()

    @tasks.loop(seconds=60)
    async def ticker(self):
        try:
            if self.carousel:
                avaxPrice = JoeSubGraph.getAvaxPrice()
                activity = "AVAX: ${}".format(round(avaxPrice, 2))
                self.carousel = False
            else:
                gasPrice = JoeSubGraph.getCurrentGasPrice()
                activity = "GAS PRICE: {}".format(round(gasPrice))
                self.carousel = True
            await discord_bot.change_presence(
                activity=discord.Activity(type=discord.ActivityType.watching, name=activity))
        except Exception as e:
            print(e)
            pass


class TaskManager(commands.Cog):
    def __init__(self, tasks):
        self.ticker.add_exception_type(KeyboardInterrupt)
        self.ticker.start()
        self.tasks = tasks

    def start(self):
        print("Starting tasks")
        for task in self.tasks:
            task.start()

    @tasks.loop(seconds=1)
    async def ticker(self):
        pass

    @ticker.after_loop
    async def onStop(self):
        for task in self.tasks:
            task.stop()

    async def getStoppedTask(self):
        for task in self.tasks:
            if not task.is_running():
                print("{} is not running".format(type(task).__name__))


@discord_bot.event
async def on_ready():
    """starts AVAX ticker"""
    print('joeBot have logged in as {0.user}'.format(discord_bot))
    taskManager = TaskManager((AvaxTicker(),))
    taskManager.start()


@discord_bot.event
async def on_command_error(ctx, error):
    return


if __name__ == '__main__':
    # Discord
    discord_bot.run(os.getenv("DISCORD_AVAXBOT_KEY"))
