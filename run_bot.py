import sys

from bots.random_bot import RandomBot
from data.storage_reader import StorageReader
from trading.bot_executor import BotExecutor
from trading.fullpass_connector import FullpassConnector
from trading.market import Market
from trading.peek_connector import PeekConnector

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
# bot = IntervalPredictionBot()
bot = RandomBot()
market = Market("EUR", market_pairs, connector)

executor = BotExecutor(bot, market, 1000.0)
executor.run()
