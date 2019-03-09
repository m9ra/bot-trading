from bots.random_bot import RandomBot
from data.storage_reader import StorageReader
from trading.bot_executor import BotExecutor
from trading.fullpass_connector import FullpassConnector
from trading.market import Market
from trading.peek_connector import PeekConnector

market_pairs = ["XRP/EUR", "XMR/EUR"]
readers = []
for pair in market_pairs:
    readers.append(StorageReader(pair))

#connector = PeekConnector(readers)
connector = FullpassConnector(readers)
# bot = IntervalPredictionBot()
bot = RandomBot()
market = Market("EUR", market_pairs, connector)

executor = BotExecutor(bot, market, 1000.0)
executor.run()
