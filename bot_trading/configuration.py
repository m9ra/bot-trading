import os

# CONFIGURATION THAT CAN BE CHANGED FREELY

TRADING_ENDPOINT = os.getenv("ENDPOINT", "packa2.cz:8697")

# defines which logging messeges will show up
# values NETWORK, CACHE, EXECUTOR, COMMAND, PORTFOLIO
LOG_LEVELS = {
    # "NETWORK",
    "CACHE",
    "EXECUTOR",
    "COMMAND",
    "PORTFOLIO"
}

LOCAL_DISK_CACHE_SIZE = 100_000_000 # maximum size of a cache file that saves network traffic (set to 0 for disabling)

USERNAME = "!!!YOUR EMAIL BELONGS HERE!!!"  # FILL IN YOUR EMAIL ADDRESS email@is.username

try:
    # this ensures invalid username is recognized
    from bot_trading.core.runtime.validation import validate_email

    username = os.getenv("BOT_USERNAME", USERNAME)
    validate_email(username)
except:
    raise AssertionError(
        f"Username `{username}` is not valid. Specify it in bot_trading.configuration.py or as USERNAME env var")
