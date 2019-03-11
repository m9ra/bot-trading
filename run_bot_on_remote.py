import sys

from bots.random_bot import RandomBot
from networking.remote_observer import RemoteObserver
from trading.bot_executor import BotExecutor
from trading.fullpass_connector import FullpassConnector
from trading.market import Market
from trading.peek_connector import PeekConnector

connector_mode = sys.argv[1]
observer = RemoteObserver("localhost:8769", "mvodolan@cz.ibm.com", "mypass")
observer.connect()

readers = observer.get_readers()
market_pairs = observer.get_pairs()

if connector_mode == "peek":
    connector = PeekConnector(readers)
elif connector_mode == "full":
    connector = FullpassConnector(readers)
else:
    raise ValueError(f"Unknown connector mode {connector_mode}. Can be peek or full")

bot = RandomBot()
market = Market("EUR", market_pairs, connector)

executor = BotExecutor(bot, market, 1000.0)
executor.run()
