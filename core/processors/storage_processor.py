import traceback
from typing import Dict

from core.processors.processor_base import ProcessorBase
from data.storage_writer import StorageWriter

ACTIVE_STORAGES: Dict[str, StorageWriter] = {}


class StorageProcessor(ProcessorBase):
    def __init__(self, pair: str):
        if pair in ACTIVE_STORAGES:
            try:
                ACTIVE_STORAGES[pair].close()
            except Exception as e:
                traceback.print_exc()

        self._pair = pair
        self._storage = StorageWriter(pair)
        ACTIVE_STORAGES[pair] = self._storage

    def write(self, *args, **kwargs):
        print(f"write {self._pair} {args + tuple(kwargs.values())}")
        self._storage.write(*args, **kwargs)

    def reset(self, is_buy: bool):
        print(f"reset {self._pair} {is_buy}")
        self._storage.reset(is_buy)

    def flush(self):
        self._storage.flush()
