import time

from bot_trading.core.data.storage_writer import StorageWriter
from bot_trading.core.processors.pricebook_processor import PricebookProcessor


class HistoryCache(object):
    def __init__(self, storage, granularity, max_history_length):
        self._storage = storage
        self._max_history_length = max_history_length
        self._current_index = storage.find_pricebook_start(time.time() - max_history_length)
        self._last_time = 0.0
        self._cache = []
        self._granularity = granularity
        self._processor = PricebookProcessor(storage.pair)

    def get_data(self):
        self._refresh_cache()
        return self._cache

    def _refresh_cache(self):
        end_index = self._storage.get_entry_count()

        for i in range(self._current_index, end_index):
            entry = self._storage.get_entry(i)
            self._processor.accept(entry)

            if not self._processor.is_ready:
                continue

            sl = self._processor.sell_levels
            bl = self._processor.buy_levels

            if not sl or not bl:
                continue

            if self._processor.current_time - self._last_time < self._granularity:
                continue

            self._last_time = self._processor.current_time
            self._cache.append({
                "u": sl[-1][0],
                "l": bl[-1][0],
                "d": self._last_time
            })

        self._current_index = end_index
        while (self._last_time - self._cache[0]["d"]) > self._max_history_length:
            self._cache.pop(0)
