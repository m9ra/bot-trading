import re
import sys
import time

from bots.baseline_bot import BaselineBot
from configuration import TRADING_ENDPOINT, INITIAL_AMOUNT
from core.networking.remote_observer import RemoteObserver
from trading.bot_executor import BotExecutor
from trading.fullpass_connector import FullpassConnector
from trading.market import Market
from trading.peek_connector import PeekConnector

HISTORY_MODE = "history"
PEEK_MODE = "peek"

if len(sys.argv) != 3:
    raise ValueError(f"Expecting command arguments: [{HISTORY_MODE}|{PEEK_MODE}] [username@is.email]")

connector_mode = sys.argv[1]
username = sys.argv[2]

if connector_mode not in [HISTORY_MODE, PEEK_MODE]:
    raise ValueError(f"Invalid connector mode {connector_mode}")

if not re.match("[^@]+@[^@]+\.[^@]+", username):
    raise ValueError(f"Username must be an email but {username} was given")

observer = RemoteObserver(TRADING_ENDPOINT, "mvodolan@cz.ibm.com", "no_password_yet")
observer.connect()

readers = observer.get_readers()
market_pairs = observer.get_pairs()

if connector_mode == PEEK_MODE:
    connector = PeekConnector(readers)
elif connector_mode == HISTORY_MODE:
    connector = FullpassConnector(readers)
else:
    raise ValueError(f"Unknown connector mode {connector_mode}. Can be peek or full")

bot = BaselineBot()
market = Market("EUR", market_pairs, connector)

executor = BotExecutor(bot, market, INITIAL_AMOUNT)
start = time.time()
executor.run()
end = time.time()

print()
print(f"RUN DURATION: {end - start}seconds")
