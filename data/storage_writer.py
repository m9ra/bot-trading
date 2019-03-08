import datetime
import os
from typing import Tuple

from core.processors.pricebook_processor import PricebookProcessor
from data.parsing import get_pair_id
from data.trade_entry import TradeEntry


class StorageWriter(object):
    root_path = "log"
    bucket_entry_count = 1000  # how often full pricebook will be written
    file_entry_count = 1_000_000

    @classmethod
    def get_storage_path(cls, pair: str, file_number: int):
        pair_id = get_pair_id(pair)
        path = os.path.join(cls.root_path, f"{pair_id}/pair_{pair_id}_{file_number}.book")
        return path

    @classmethod
    def get_file_index(cls, entry_index: int) -> Tuple[int, int]:
        return int(entry_index / cls.file_entry_count), entry_index % cls.file_entry_count

    def __init__(self, pair: str):
        self._pair = pair
        dirpath = os.path.dirname(self.get_storage_path(self._pair, 0))
        os.makedirs(dirpath, exist_ok=True)

        self._next_entry_index = self._load_entry_index()
        self._pricebook = PricebookProcessor(self._pair)
        self._current_file = None

    def _load_entry_index(self):
        i = 0
        while True:
            i += 1
            file_path = self.get_storage_path(self._pair, i)
            if not os.path.exists(file_path):
                i -= 1
                if i == 0:
                    return 0

                size = os.path.getsize(self.get_storage_path(self._pair, i))
                return i * self.file_entry_count + int(size / TradeEntry.chunk_size)

    def _open_next_file(self):
        file_number = int(self._next_entry_index / self.file_entry_count)
        path = self.get_storage_path(self._pair, file_number)

        abs_path = os.path.abspath(path)
        return open(abs_path, "ab")

    def write(self, is_buy: bool, price: float, volume: float, timestamp: float):
        self._handle_write(is_buy, price, volume, timestamp, is_reset=False)

    def reset(self, is_buy):
        self._handle_write(is_buy, 0.0, 0.0, datetime.datetime.utcnow().timestamp(), is_reset=True)

    def flush(self):
        self._current_file.flush()

    def _handle_write(self, is_buy, price, volume, timestamp, is_reset):
        entry = TradeEntry.create_entry(self._pair, is_buy, price, volume, timestamp, is_reset, is_service=False)

        self._pricebook.accept(entry)

        need_new_file = self._next_entry_index % self.file_entry_count == 0
        need_new_bucket = self._next_entry_index % self.bucket_entry_count == 0

        if not need_new_bucket and not need_new_file:
            # simple write through
            chunk = TradeEntry.to_chunk(entry)
            self._write_chunk(chunk)
            return  # a usual entry, no special action to handle it
        elif not self._pricebook.is_ready:
            return  # wait until pricebook is initialized (for the first time, when service record is to be created)

        if need_new_file:
            if self._current_file:
                self._current_file.close()
            self._current_file = None

        if need_new_bucket:
            service_entries = self._pricebook.dump_to_entries()
            for entry in service_entries:
                chunk = TradeEntry.to_chunk(entry)
                self._write_chunk(chunk)

    def _write_chunk(self, chunk):
        if self._current_file is None:
            self._current_file = self._open_next_file()
        self._current_file.write(bytes(chunk))
        self._next_entry_index += 1
