from typing import Dict

from bot_trading.core.data.storage_writer import StorageWriter
from bot_trading.core.processors.processor_base import ProcessorBase

ACTIVE_STORAGES: Dict[str, StorageWriter] = {}


class StorageProcessor(ProcessorBase):
    def __init__(self, pair: str):
        if pair not in ACTIVE_STORAGES:
            ACTIVE_STORAGES[pair] = StorageWriter(pair)

        self._storage = ACTIVE_STORAGES[pair]
        self._pair = pair

    def write(self, *args, **kwargs):
        print(f"write {self._pair} {args + tuple(kwargs.values())}")
        self._storage.write(*args, **kwargs)

    def reset(self, is_buy: bool):
        print(f"reset {self._pair} {is_buy}")
        self._storage.reset(is_buy)

    def flush(self):
        self._storage.flush()
