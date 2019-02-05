import datetime
import os
import struct

from typing import List


class Storage(object):
    root_path = "log"

    @classmethod
    def get_pair_id(cls, pair: str):
        return pair.lower().replace("/", "_")

    @classmethod
    def float_to_8b(cls, value: float) -> List:
        result = list(bytearray(struct.pack("d", value)))
        if len(result) != 8:
            raise AssertionError(f"Float encoding produces incorrect format {result}")

        return result

    def __init__(self, pair: str):
        pair_id = Storage.get_pair_id(pair)
        path = os.path.join(Storage.root_path, f"pair_{pair_id}.book")

        directory = os.path.dirname(path)
        os.makedirs(directory, exist_ok=True)

        self._abs_path = os.path.abspath(path)
        self._file = open(self._abs_path, "ab")

    def write(self, is_buy: bool, price: float, volume: float, timestamp: float):
        buy_byte = 1 if is_buy else 0
        self._write_raw(buy_byte, price, volume, timestamp)

    def _write_raw(self, buy_byte, price, volume, timestamp):
        chunk = [buy_byte] + Storage.float_to_8b(price) + Storage.float_to_8b(volume) + Storage.float_to_8b(timestamp)
        self._file.write(bytearray(chunk))

    def reset(self, is_buy):
        buy_byte = 255 if is_buy else 254
        self._write_raw(buy_byte, 0, 0, datetime.datetime.utcnow().timestamp())
