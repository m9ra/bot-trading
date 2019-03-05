from typing import List


class StorageIndex(object):
    def __init__(self):
        self._entry_indexes: List[int] = []
        self._timestamps: List[float] = []

    def get_pricebook_start(self, timestamp):
        raise NotImplementedError()
