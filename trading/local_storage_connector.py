from queue import Queue
from typing import List

from data.parsing import make_pair, parse_pair, reverse_pair
from data.storage_reader import StorageReader
from data.trade_entry import TradeEntry
from trading.connector_base import ConnectorBase
from trading.fullpass_storage_connector import FullpassStorageConnector
from trading.pricebook_view import PricebookView
from trading.pricebook_view_provider import PricebookViewProvider


class LocalStorageConnector(FullpassStorageConnector):
    def __init__(self, storage_readers):
        self._entry_queue = Queue()

        super().__init__(storage_readers)

    def _on_new_entries(self, entries: List[TradeEntry]):
        for entry in entries:
            self._entry_queue.put(entry)
