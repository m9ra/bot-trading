import sys
import time

from bot_trading.bots import BaselineBot
from bot_trading.core import StorageReader
from bot_trading.trading import BotExecutor
from bot_trading.trading import FullpassConnector
from bot_trading.trading import Market
from bot_trading.trading.peek_connector import PeekConnector

connector_mode = sys.argv[1]

market_pairs = ["XRP/EUR", "XMR/EUR", "ETH/EUR", "REP/EUR"]
readers = []
for pair in market_pairs:
    readers.append(StorageReader(pair))

if connector_mode == "peek":
    connector = PeekConnector(readers)
elif connector_mode == "full":
    connector = FullpassConnector(readers)
else:
    raise ValueError(f"Unknown connector mode {connector_mode}. Can be peek or full")

bot = BaselineBot()
market = Market("EUR", market_pairs, connector)

executor = BotExecutor(bot, market, 1000.0)
start = time.time()
executor.run()
end = time.time()

print()
print(f"RUN DURATION: {end - start}")
