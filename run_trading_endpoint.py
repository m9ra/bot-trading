import time

from data.storage_reader import StorageReader
from networking.trading_endpoint import TradingEndpoint

market_pairs = ["XRP/EUR", "XMR/EUR", "ETH/EUR", "REP/EUR"]
readers = []
for pair in market_pairs:
    readers.append(StorageReader(pair))

endpoint = TradingEndpoint(readers)
endpoint.start_accepting(8769)

while True:
    time.sleep(1)
