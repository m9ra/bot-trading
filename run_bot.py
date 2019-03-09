from bots.random_bot import RandomBot
from data.storage_reader import StorageReader
from trading.bot_executor import BotExecutor
from trading.storage_peek_connector import StoragePeekConnector
from trading.market import Market

market_pairs = ["XRP/EUR", "XMR/EUR"]
readers = []
for pair in market_pairs:
    readers.append(StorageReader(pair))

connector = StoragePeekConnector(readers)
# bot = IntervalPredictionBot()
bot = RandomBot()
market = Market("EUR", market_pairs, connector)

executor = BotExecutor(bot, market, 1000.0)
executor.run()
