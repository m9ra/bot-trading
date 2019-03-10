from typing import Callable, List

from data.trade_entry import TradeEntry


class EntryReaderBase(object):
    def get_entry_count(self) -> int:
        raise NotImplementedError("must be overridden")

    def get_entry(self, entry_index: int) -> TradeEntry:
        raise NotImplementedError("must be overridden")

    def find_pricebook_start(self, start_time: float) -> int:
        raise NotImplementedError("must be overridden")

    def subscribe(self, follower: Callable[[int, List[TradeEntry]], None]):
        raise NotImplementedError("must be overriden")

    @property
    def pair(self) -> str:
        return self._pair

    def __init__(self, pair: str):
        self._pair = pair
