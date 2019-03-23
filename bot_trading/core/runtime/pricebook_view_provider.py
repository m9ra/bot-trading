from typing import Optional

from bot_trading.core.data.pricebook_processor_state import PricebookProcessorState
from bot_trading.core.messages import log_cache
from bot_trading.trading.pricebook_view import PricebookView


class PricebookViewProvider(object):
    # how many view states will be kept for this provider in cache
    cached_pricebook_view_state_count_limit = 20

    # how long fast forwarding update for a cache entry can be issued
    fast_forward_cache_seconds_limit = 200.0

    def __init__(self, reader):
        self._reader = reader

        self._state_cache = []

    def get_pricebook_view(self, timestamp: float):
        reader = self._reader

        cached_state = self._get_fastforwardable_cache_entry(timestamp)
        is_cache_miss = False
        if cached_state is None:
            # nothing helpful in the cache was found
            # create state from scratch
            is_cache_miss = True
            start_index = reader.find_pricebook_start(timestamp)
            log_cache(f"Requested remote pricebook start {reader.pair} {timestamp} start: {start_index}")
            cached_state = PricebookProcessorState(start_index, 0.0)

        view = PricebookView(cached_state, reader)
        was_full_sync = view.fast_forward_to(timestamp)
        if is_cache_miss:
            new_state = view._dump_state()
            new_state.current_time = timestamp
            self._put_to_cache(new_state)

        if view._current_time - cached_state.current_time > self.fast_forward_cache_seconds_limit / self.cached_pricebook_view_state_count_limit:
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
