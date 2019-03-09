from queue import Queue
from typing import List

from data.storage_reader import StorageReader
from data.trade_entry import TradeEntry
from trading.fullpass_storage_connector import FullpassStorageConnector


class StoragePeekConnector(FullpassStorageConnector):
    def __init__(self, storage_readers: List[StorageReader]):
        super().__init__(storage_readers)

        # subscribe to all the readers for updates
        self._entry_queue = Queue()
        for storage_reader in storage_readers:
            storage_reader.subscribe(self._on_new_entries)

    def _on_new_entries(self, first_entry_index: int, entries: List[TradeEntry]):
        current_entry_index = first_entry_index
        for entry in entries:
            self._entry_queue.put((current_entry_index, entry))
            current_entry_index += 1

    def next_entry(self):
        entry_index, entry = self._entry_queue.get(block=True)
        return entry
