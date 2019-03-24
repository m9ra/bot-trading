from threading import Event, RLock
from typing import List, Any, Optional, Callable

from bot_trading.core.data.storage_writer import StorageWriter
from bot_trading.core.data.trade_entry import TradeEntry


class BucketCache(object):
    _not_requested = "entry_was_not_requested_yet"

    @property
    def is_complete(self):
        return self._write_count >= StorageWriter.bucket_entry_count

    def __init__(self, pair, bucket_id: int, async_bucket_requester: Callable[[str, int], None]):
        self._pair = pair
        self._bucket_id = bucket_id
        self._async_bucket_requester = async_bucket_requester

        self._is_requested = False
        self._write_count = 0
        self._L_entries = RLock()

        self._entries: List[Any] = [self._not_requested] * StorageWriter.bucket_entry_count

    def close(self):
        if self.is_complete:
            return  # no one can be blocked here

        for entry in self._entries:
            if isinstance(entry, Event):
                entry.set()  # release all the requesters

    def write(self, bucket_offset: int, entry: TradeEntry):
        with self._L_entries:
            old_entry = self._entries[bucket_offset]
            if not isinstance(old_entry, TradeEntry):
                self._write_count += 1

            self._entries[bucket_offset] = entry

        if isinstance(old_entry, Event):
            old_entry.set()  # wake up whoever was waiting there

    def read(self, bucket_offset: int, requesting_is_allowed: bool) -> Optional[TradeEntry]:
        entry = self._entries[bucket_offset]
        if isinstance(entry, TradeEntry):
            return entry  # optimistic reading

        with self._L_entries:
            # read again because entry may be changed meanwhile
            entry = self._entries[bucket_offset]
            if isinstance(entry, TradeEntry):
                return entry

            if entry is self._not_requested and not requesting_is_allowed:
                # blocking is not allowed - end here
                return None

            event: Event = None
            if entry is self._not_requested:
                # we can request and block here
                event = Event()
                self._entries[bucket_offset] = event

                if not self._is_requested:
                    self._async_bucket_requester(self._pair, self._bucket_id)
                    self._is_requested = True  # this avoid multiple requests

            elif entry is Event:
                event = entry

        if event is not None:
            event.wait()  # wait until the entry comes

        entry = self._entries[bucket_offset]
        if isinstance(entry, Event):
            return None  # interruption may cause that entry is not received

        return entry
