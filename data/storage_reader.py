import struct
from io import SEEK_SET, SEEK_END
from math import floor
from typing import Tuple, Optional

from data.storage_writer import StorageWriter
from data.trade_entry import TradeEntry


class StorageReader(object):
    def __init__(self, pair):
        self.pair = pair
        path = StorageWriter.get_storage_path(pair)
        self._file = open(path, "rb")
        self._peek_entry_index = 0

    def get_peek_entry(self) -> TradeEntry:
        return self._parse_entry(self._peek_entry_index)

    def get_entry(self, index):
        return self._parse_entry(index)

    def shift_to_next_entry(self):
        self._peek_entry_index += 1

    def get_peek_index(self) -> int:
        return self._peek_entry_index

    def get_date_range(self) -> Optional[Tuple[float, float]]:
        entry_count = self.get_entry_count()
        if entry_count == 0:
            return None

        first_entry = self._parse_entry(0)
        last_entry = self._parse_entry(entry_count - 1)
        return (first_entry.timestamp, last_entry.timestamp)

    def get_entry_count(self):
        self._file.seek(0, SEEK_END)
        length = self._file.tell()
        return int(floor(length / StorageWriter.entry_size))

    def validate_date_sequence(self):
        last_timestamp = 0
        for i in range(self.get_entry_count()):
            timestamp = self._parse_entry(i).timestamp
            if timestamp < last_timestamp:
                for j in range(max(0, i - 20), min(self.get_entry_count(), i + 20)):
                    if j == i:
                        print("==>", end="")
                    print(self._parse_entry(j))
                raise AssertionError(f"sequence is not consistent at {i} for {last_timestamp} vs {timestamp}")

            last_timestamp = timestamp

    def find_book_entries(self, start: float, end: float, book_size: int):
        entry_count = self.get_entry_count()
        if entry_count <= 0:
            return None

        _, date_end = self.get_date_range()
        if start > date_end:
            # search is out of the interval
            return []

        current_position = self.find_pricebook_start(start, book_size)

        # collect the window
        result = []
        while True:
            entry = self._parse_entry(current_position)
            if entry.timestamp <= end:
                result.append(entry)
            else:
                break

            current_position += 1
            if current_position >= entry_count:
                break

        return result

    def find_pricebook_start(self, start, book_size):
        current_position = 0
        interval_start = 0
        interval_end = self.get_entry_count()
        # find the start (binary search)
        while interval_end - interval_start > 1:
            current_position = int((interval_end + interval_start) / 2)
            self.get_entry(current_position)
            current_entry = self._parse_current_entry()
            timestamp = current_entry.timestamp
            for i in range(1, book_size * 2 + 2):
                expanded_position = current_position - i
                if expanded_position < 0:
                    break

                entry = self.get_entry(expanded_position)
                timestamp = max(timestamp, entry.timestamp)

            if timestamp > start:
                interval_end = current_position
            else:
                interval_start = current_position
        # find enough changes back in time for the book
        book_info_sizes = {True: 0, False: 0}
        while book_info_sizes[True] < book_size or book_info_sizes[False] < book_size:
            current_entry = self._parse_entry(current_position)

            current_position -= 1
            if current_position <= 0:
                break

            count = book_info_sizes[current_entry.is_buy]
            count += 1
            if current_entry.volume <= 0:
                count -= 2  # compensate for some previous entry that was deleted on this point

            if current_entry.is_reset:
                count = 0  # whole book was potentially deleted at this time

            book_info_sizes[current_entry.is_buy] = max(0, count)

        return current_position

    def _parse_entry(self, index):
        self._seek_entry(index)
        current_entry = self._parse_current_entry()
        return current_entry

    def _parse_current_entry(self) -> TradeEntry:
        chunk = self._file.read(StorageWriter.entry_size)

        if len(chunk) != StorageWriter.entry_size:
            raise AssertionError(f"Incorrect chunk returned: {chunk}")

        return TradeEntry(self.pair, chunk)

    def _seek_entry(self, index):
        self._file.seek(index * StorageWriter.entry_size, SEEK_SET)
