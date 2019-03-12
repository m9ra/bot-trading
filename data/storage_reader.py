import os
from io import SEEK_SET, SEEK_END
from math import floor
from threading import Lock
from typing import Tuple, Optional, List, Callable

from data.entry_reader_base import EntryReaderBase
from data.storage_writer import StorageWriter
from data.trade_entry import TradeEntry


class StorageReader(EntryReaderBase):
    def __init__(self, pair):
        self._files = {}
        self._known_last_file_index = 0

        self._subscribers: List = None

        super().__init__(pair)

    def get_entry_count(self):
        file = self._get_last_file()
        return self._get_file_entry_count(file)

    def get_date_range(self) -> Optional[Tuple[float, float]]:
        entry_count = self.get_entry_count()
        if entry_count == 0:
            return None

        first_entry = self._parse_entry(0)
        last_entry = self._parse_entry(entry_count - 1)
        return (first_entry.timestamp, last_entry.timestamp)

    def get_entry(self, index):
        return self._parse_entry(index)

    def get_bucket_count(self):
        return int(self.get_entry_count() / StorageWriter.bucket_entry_count)

    def find_pricebook_start(self, target):
        interval_start = 0
        interval_end = self.get_bucket_count() - 1
        current_entry = None
        # find the nearest lower index (binary search on buckets)
        while interval_end - interval_start > 1 or current_entry.timestamp > target:
            current_bucket = int((interval_end + interval_start) / 2)
            current_position = current_bucket * StorageWriter.bucket_entry_count
            current_entry = self.get_entry(current_position)

            if target < current_entry.timestamp:
                interval_end = current_bucket
            else:
                interval_start = current_bucket

            if interval_start == interval_end:
                break

        return current_bucket * StorageWriter.bucket_entry_count

    def get_bucket_chunk(self, bucket_index):
        bucket_size = StorageWriter.bucket_entry_count
        start_entry_index = bucket_index * bucket_size
        end_entry_index = min(start_entry_index + bucket_size, self.get_entry_count())

        chunk_size = int((end_entry_index - start_entry_index) * TradeEntry.chunk_size)
        file, in_file_index = self._get_file(start_entry_index)
        start_offset = int(in_file_index * TradeEntry.chunk_size)

        # todo add locking
        file.seek(start_offset, SEEK_SET)
        return file.read(chunk_size)

    def subscribe(self, feed_handler: Callable[[int, List[TradeEntry]], None]):
        if self._subscribers:
            self._subscribers.append(feed_handler)
            return

            # otherwise initialize event handling
        self._subscribers = [feed_handler]

        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
        from watchdog.observers.inotify_buffer import InotifyBuffer
        InotifyBuffer.delay = 0

        storage = self

        class Handler(FileSystemEventHandler):
            def __init__(self):
                self._next_entry_index = None
                self._L_event = Lock()

            def on_modified(self, event):
                with self._L_event:
                    file_index = storage._get_last_file_index()
                    file = storage._get_file_by_index(file_index)
                    file_end = file.seek(0, SEEK_END)
                    entry_index = int(file_end / TradeEntry.chunk_size) + file_index * StorageWriter.file_entry_count

                    if self._next_entry_index is None:
                        # first event - just initialize
                        self._next_entry_index = entry_index
                        return

                    result = []
                    for i in range(self._next_entry_index, entry_index):
                        result.append(storage.get_entry(i))

                    if result:
                        for subscriber in storage._subscribers:
                            subscriber(self._next_entry_index, result)

                    self._next_entry_index = entry_index

        directory = os.path.dirname(StorageWriter.get_storage_path(self.pair, 0))
        event_handler = Handler()
        observer = Observer(timeout=100)
        observer.schedule(event_handler, directory, recursive=False)
        observer.start()

    def _parse_entry(self, entry_index) -> Optional[TradeEntry]:
        file, in_file_entry_index = self._get_file(entry_index)
        if file is None:
            return None

        chunk_size = TradeEntry.chunk_size
        file.seek(in_file_entry_index * chunk_size, SEEK_SET)
        chunk = file.read(chunk_size)

        if len(chunk) == 0:
            return None

        if len(chunk) != chunk_size:
            raise AssertionError(f"Incorrect chunk returned: {chunk}")

        return TradeEntry(self.pair, chunk)

    def _get_file(self, entry_index):
        file_index, in_file_index = StorageWriter.get_file_index(entry_index)
        file = self._get_file_by_index(file_index)

        return file, in_file_index

    def _get_file_by_index(self, file_index):
        if file_index not in self._files:
            path = StorageWriter.get_storage_path(self.pair, file_index)
            if not os.path.exists(path):
                return None

            self._files[file_index] = open(path, "rb")
            self._known_last_file_index = max(self._known_last_file_index, file_index)

        return self._files[file_index]

    def _get_last_file_index(self):
        if self._known_last_file_index in self._files:
            entry_count = self._get_file_entry_count(self._files[self._known_last_file_index])

            if entry_count < StorageWriter.file_entry_count:
                # then known last file is not filled yet -> its really the last file
                return self._known_last_file_index

        # otherwise search for the really last file
        i = 0
        while True:
            path = StorageWriter.get_storage_path(self.pair, i)
            if not os.path.exists(path):
                break

            i += 1

        last_index = i - 1
        self._known_last_file_index = last_index
        return last_index

    def _get_last_file(self):
        index = self._get_last_file_index()
        return self._get_file_by_index(index)

    def _get_file_entry_count(self, file):
        if file is None:
            return 0

        file.seek(0, SEEK_END)
        length = file.tell()
        return int(floor(length / TradeEntry.chunk_size))
