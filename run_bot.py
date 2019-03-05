from bots.interval_prediction_bot import IntervalPredictionBot
from bots.random_bot import RandomBot
from data.storage_reader import StorageReader
from trading.bot_executor import BotExecutor
from trading.fund import Fund
from trading.local_storage_connector import LocalStorageConnector
from trading.market import Market

market_pairs = ["ADA/EUR", "XMR/EUR"]
readers = []
for pair in market_pairs:
    readers.append(StorageReader(pair))

connector = LocalStorageConnector(readers)
# bot = IntervalPredictionBot()
bot = RandomBot()
market = Market("EUR", market_pairs, connector)

market.next_step()

history = market.get_history2(0)
print(history.get_value(Fund(10, "EUR")))
print(history.get_value(Fund(10, "XMR")))
print(history.after_conversion(Fund(373.8, "EUR"), "XMR"))

executor = BotExecutor(bot, market, 1000.0)
executor.run()
