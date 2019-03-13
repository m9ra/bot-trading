import datetime
import time

from configuration import LOG_LEVELS


def log_cache(message):
    log("CACHE", message)


def log_network(message):
    log("NETWORK", message)


def log_executor(*args, **kwargs):
    if "EXECUTOR" in LOG_LEVELS:
        print(*args, **kwargs)


def log_fund(message):
    log("FUND", message)


def log_command(message) -> object:
    log("COMMAND", message)


def log(log_level, message, **kwargs):
    if log_level not in LOG_LEVELS:
        return

    print(str(datetime.datetime.now()) + f" [{log_level}] {message}", **kwargs)
