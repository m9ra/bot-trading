from bot_trading.core.data.storage_writer import StorageWriter
from bot_trading.core.processors.pricebook_processor import PricebookProcessor


class HistoryCache(object):
    def __init__(self, storage, max_history_length, max_history_duration):
        self._storage = storage
        self._max_history_length = max_history_length
        self._max_history_duration = max_history_duration
        self._current_index = 0
        self._last_time = 0.0
        self._cache = []
        self._processor = PricebookProcessor(storage.pair)

    def get_data(self):
        self._refresh_cache()
        return self._cache

    def _refresh_cache(self):
        end_index = self._storage.get_entry_count()
        desired_index = max(0, end_index - self._max_history_length)

        if desired_index - self._current_index > 10 * StorageWriter.bucket_entry_count:
            # create new processor
            bucket_start_index = int(
                desired_index / StorageWriter.bucket_entry_count) * StorageWriter.bucket_entry_count

            self._processor = PricebookProcessor(self._storage.pair)
            self._last_time = 0.0
            self._cache = []
            self._current_index = bucket_start_index

        for i in range(self._current_index, end_index):
            entry = self._storage.get_entry(i)
            self._processor.accept(entry)

            if not self._processor.is_ready:
                continue

            sl = self._processor.sell_levels
            bl = self._processor.buy_levels

            if not sl or not bl:
                continue

            if self._processor.current_time - self._last_time < 1.0:
                continue

            self._last_time = self._processor.current_time
            self._cache.append({
                "u": sl[-1][0],
                "l": bl[-1][0],
                "d": self._last_time
            })

        self._current_index = end_index
        while len(self._cache) > self._max_history_length or (
                self._last_time - self._cache[0]["d"]) > self._max_history_duration:
            self._cache.pop(0)
