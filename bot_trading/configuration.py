import os

# CONFIGURATION THAT CAN BE CHANGED

TRADING_ENDPOINT = os.getenv("ENDPOINT", "packa2.cz:8697")
INITIAL_AMOUNT = 1000.0
TARGET_CURRENCY = "EUR"

# defines which logging messeges will show up
# values NETWORK, CACHE, EXECUTOR, COMMAND, PORTFOLIO
LOG_LEVELS = {
    # "NETWORK",
    "CACHE",
    "EXECUTOR",
    "COMMAND",
    "PORTFOLIO"
}
