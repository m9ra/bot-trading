import time

from bot_trading.configuration import TRADING_ENDPOINT
from bot_trading.core.data.storage_reader import StorageReader
from bot_trading.core.networking.trading_endpoint import TradingEndpoint

market_pairs = ["XRP/EUR", "XMR/EUR", "ETH/EUR", "REP/EUR"]
readers = []
for pair in market_pairs:
    readers.append(StorageReader(pair))

endpoint = TradingEndpoint(readers)
endpoint.start_accepting(int(TRADING_ENDPOINT.split(":")[-1]))

while True:
    time.sleep(1)
