import asyncio
from contextlib import suppress

from discord.ext import commands, tasks
from abc import abstractmethod


def readable(nb, n_decimals=0):
    if n_decimals == 0:
        return '{:,}'.format(int(nb))
    else:
        return '{:,}'.format(round(nb, n_decimals))


def humanFormat(nb, n_decimals):
    magnitude = 0
    while abs(nb) >= 1000:
        magnitude += 1
        nb /= 1000.0
    # add more suffixes if you need them
    return '%.{}f%s'.format(n_decimals) % (nb, ['', 'K', 'M', 'G', 'T', 'P'][magnitude])


def smartRounding(nb, n_decimals=2):
    if nb < 1:
        if "e" in str(nb):
            return roundScientific(nb, n_decimals)
        else:
            decimals = str(nb)[2:]
            nb = int(decimals)
            n_zero = len(decimals) - len(str(nb))
            round_up = int(str(nb)[n_decimals]) // 5
            return "0.{}{}".format("0" * n_zero, int(str(nb)[:n_decimals]) + round_up)
    return humanFormat(nb, n_decimals)


def roundScientific(nb, decimals=-1):
    nb, exp = str(nb).split("e")
    if decimals == -1:
        return "{}e{}".format(nb, exp)
    else:
        return "{}e{}".format(nb[:decimals + 2], exp)


class TaskManager(commands.Cog):
    def __init__(self, tasks_to_run):
        self.ticker.add_exception_type(KeyboardInterrupt)
        self.ticker.start()
        self.tasks = {type(task).__name__: task for task in tasks_to_run}

    def start(self):
        for task_name in self.tasks.keys():
            self.startTask(task_name)
        return self.getRunningTasks()

    @tasks.loop(seconds=1)
    async def ticker(self):
        pass

    @ticker.after_loop
    async def onStop(self):
        for task_name in self.tasks.keys():
            self.stopTask(task_name)
        return self.getStoppedTasks()

    def startTask(self, task_name):
        if task_name in self.tasks:
            self.stopTask(task_name)
        if self.tasks[task_name].start():
            return "Starting {}".format(task_name)
        return "{} already running".format(task_name)

    def stopTask(self, task_name):
        if self.tasks[task_name].stop():
            return "Stopping {}".format(task_name)
        return "{} not running".format(task_name)

    def getStoppedTasks(self):
        stopped_tasks = []
        for name, task in self.tasks.items():
            if not task.is_running():
                stopped_tasks.append(name)
        return "Not running : {}".format(stopped_tasks)

    def getRunningTasks(self):
        running_task = []
        for name, task in self.tasks.items():
            if task.is_running():
                running_task.append(name)
        return "Running : {}".format(running_task)

    def getAllTasks(self):
        return "All tasks : {}".format(list(self.tasks.keys()))


# Parent class
# All tasks needs to inherit from this
class Ticker:
    def start(self):
        if not self.is_running():
            self.ticker.start()
            return True
        return False

    def stop(self):
        if self.is_running():
            self.ticker.cancel()
            return True
        return False

    def is_running(self):
        return self.ticker.is_running()

    @abstractmethod
    def ticker(self):
        pass
