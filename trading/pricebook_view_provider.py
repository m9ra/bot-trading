from typing import Optional

from configuration import BOOK_DEPTH
from trading.pricebook_view import PricebookView
from data.pricebook_processor_state import PricebookProcessorState


class PricebookViewProvider(object):
    # how many view states will be kept for this provider in cache
    cached_pricebook_view_state_count_limit = 20

    # how long fast forwarding update for a cache entry can be issued
    fast_forward_cache_seconds_limit = 20.0

    def __init__(self, reader):
        self._reader = reader

        self._state_cache = []

    def get_pricebook_view(self, timestamp: float):
        reader = self._reader

        end_index = reader.get_peek_index()
        cached_state = self._get_fastforwardable_cache_entry(timestamp)
        if cached_state is None:
            # nothing helpful in the cache was found
            # create state from scratch
            print(f"Cache miss: {timestamp}")

            start_index = reader.find_pricebook_start(timestamp, BOOK_DEPTH)
            start_index = min(start_index, end_index)
            print(f"{self._reader.pair} {timestamp} start: {start_index}, end: {end_index}")
            cached_state = PricebookProcessorState(start_index, 0)

        view = PricebookView(cached_state, reader, end_index)
        view.fast_forward_to(timestamp)

        if view._current_time - cached_state.current_time > 2 * self.fast_forward_cache_seconds_limit / self.cached_pricebook_view_state_count_limit:
            new_state = view._dump_state()
            self._put_to_cache(new_state)

        return view

    def _get_fastforwardable_cache_entry(self, timestamp) -> Optional[PricebookProcessorState]:

        best_state = None
        best_forward_time = float("inf")
        for state in self._state_cache:
            forward_time = timestamp - state.current_time

            if forward_time < 0:
                # we can only go forward
                continue

            if forward_time > PricebookViewProvider.fast_forward_cache_seconds_limit:
                # forwarding would be too far
                continue

            if best_forward_time > forward_time:
                best_state = state
                best_forward_time = forward_time

        return best_state

    def _put_to_cache(self, state: PricebookProcessorState):
        while len(self._state_cache) + 1 >= PricebookViewProvider.cached_pricebook_view_state_count_limit:
            del self._state_cache[-1]

        self._state_cache.insert(0, state)
