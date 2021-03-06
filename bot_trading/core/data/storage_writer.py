import datetime
import os
from typing import Tuple, List

from bot_trading.core.data.parsing import get_pair_id
from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.core.processors.pricebook_processor import PricebookProcessor


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

        self._buffer: List[TradeEntry] = []

    def _load_entry_index(self):
        i = 0
        while True:
            next_file_path = self.get_storage_path(self._pair, i)
            if not os.path.exists(next_file_path):
                break

            i += 1

        i -= 1  # go to previous storage index which should exist
        if i < 0:
            # unless no storage exists
            return 0

        path = self.get_storage_path(self._pair, i)
        size = os.path.getsize(path)
        if size % TradeEntry.chunk_size != 0:
            with open(path, "w") as f:
                f.seek(int(size / TradeEntry.chunk_size) * TradeEntry.chunk_size, os.SEEK_SET)
                f.truncate()
                raise AssertionError(f"Invalid alignment detected for {path}")

        return i * self.file_entry_count + int(size / TradeEntry.chunk_size)

    def _open_next_file(self):
        file_number = int(self._next_entry_index / self.file_entry_count)
        path = self.get_storage_path(self._pair, file_number)

        abs_path = os.path.abspath(path)
        return open(abs_path, "ab")

    def write(self, is_buy: bool, price: float, volume: float, timestamp: float):
        entry = TradeEntry.create_entry(self._pair, is_buy, price, volume, timestamp, False, is_flush=False)
        self._buffer.append(entry)

    def reset(self, is_buy):
        entry = TradeEntry.create_entry(self._pair, is_buy, 0.0, 0.0, datetime.datetime.utcnow().timestamp(),
                                        is_reset=True, is_flush=False)
        self._buffer.append(entry)

    def flush(self):
        if not self._buffer:
            return  # nothing to do here

        self._buffer[-1].is_flush_entry = True
        for entry in self._buffer:
            self._handle_write(entry)

        self._buffer = []

        self._current_file.flush()

    def _handle_write(self, entry):
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
