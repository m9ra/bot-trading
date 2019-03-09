class EntryReaderBase(object):
    def get_entry_count(self):
        raise NotImplementedError("must be overridden")

    def get_entry(self, entry_index: int):
        raise NotImplementedError("must be overridden")

    @property
    def pair(self) -> str:
        return self._pair

    def __init__(self, pair: str):
        self._pair = pair
