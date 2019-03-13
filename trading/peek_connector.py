from queue import Queue
from typing import List

from core.data.entry_reader_base import EntryReaderBase
from core.data.trade_entry import TradeEntry
from trading.connector_base import ConnectorBase


class PeekConnector(ConnectorBase):
    def __init__(self, entry_readers: List[EntryReaderBase]):
        super().__init__(entry_readers)

        # subscribe to all the readers for updates
        self._entry_queue = Queue()
        for storage_reader in entry_readers:
            storage_reader.subscribe(self._on_new_entries)

    def _on_new_entries(self, first_entry_index: int, entries: List[TradeEntry]):
        current_entry_index = first_entry_index
        for entry in entries:
            if entry is None:
                continue

            self._entry_queue.put((current_entry_index, entry))
            current_entry_index += 1

    def blocking_get_next_entry(self):
        entry_index, entry = self._entry_queue.get(block=True)
        return entry
