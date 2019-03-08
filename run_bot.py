from bots.random_bot import RandomBot
from data.storage_reader import StorageReader
from trading.bot_executor import BotExecutor
from trading.local_storage_connector import LocalStorageConnector
from trading.market import Market

market_pairs = ["XRP/EUR"]
readers = []
for pair in market_pairs:
    readers.append(StorageReader(pair))

connector = LocalStorageConnector(readers)
# bot = IntervalPredictionBot()
bot = RandomBot()
market = Market("EUR", market_pairs, connector)

executor = BotExecutor(bot, market, 1000.0)
executor.start()

connector.run()
