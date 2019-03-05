from typing import List

from core.processors.pricebook_processor import PricebookProcessor
from data.pricebook_processor_state import PricebookProcessorState


class StorageIndex(object):
    def __init__(self, pair):
        self._states: List[PricebookProcessorState] = []
        self.next_entry = 0
        self._processor = PricebookProcessor(pair)

    def get_pricebook_start(self, timestamp):
        raise NotImplementedError()

    def update_by(self, entries):
        for entry in entries:
            self._processor.accept(entry)

            self.next_entry += 1
            if self.next_entry % 1000 == 0:
                state = PricebookProcessorState(self.next_entry - 1, self._processor._current_time)
                state.load_from(self._processor)
                self._states.append(state)
