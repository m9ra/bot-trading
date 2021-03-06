import struct

from typing import List


class TradeEntry(object):
    chunk_size = 1 + 3 * 8

    def __init__(self, pair: str, chunk):
        self.pair = pair
        self.price: float = None
        self.volume: float = None
        self.timestamp: float = None
        self.real_utc_timestamp: float = None

        # buy_byte + 8b price + 8b volume + 8b timestamp
        info_byte, self.price, self.volume, self.timestamp = struct.unpack("<Bddd", chunk)

        self.is_buy = bool(info_byte & 1)
        self.is_reset = bool(info_byte & 2)
        self.is_flush_entry = bool(info_byte & 4)

        if self.is_reset and not self.is_flush_entry:
            self.real_utc_timestamp = self.timestamp

    @classmethod
    def create_chunk(cls, is_buy, price, volume, timestamp, is_reset, is_flush):
        info_byte = 1 if is_buy else 0
        if is_reset:
            info_byte |= 2
        if is_flush:
            info_byte |= 4

        chunk = [info_byte] + cls.float_to_8b(price) + cls.float_to_8b(volume) + cls.float_to_8b(timestamp)
        return bytes(chunk)

    @classmethod
    def to_chunk(cls, entry: 'TradeEntry'):
        return cls.create_chunk(entry.is_buy, entry.price, entry.volume, entry.timestamp,
                                entry.is_reset, entry.is_flush_entry)

    @classmethod
    def create_entry(cls, pair, is_buy, price, volume, timestamp, is_reset, is_flush):
        chunk = cls.create_chunk(is_buy, price, volume, timestamp, is_reset, is_flush)
        return TradeEntry(pair, chunk)

    def __repr__(self):
        mode = "buy" if self.is_buy else "sell"
        result = f"{self.timestamp} {self.pair} {mode} volume: {self.volume}, price: {self.price}"

        if self.is_reset:
            result = "reset " + result

        if self.is_flush_entry:
            result = "is_flush " + result

        return result

    @classmethod
    def float_to_8b(cls, value: float) -> List:
        if not isinstance(value, float):
            raise AssertionError(f"Float is expected")

        result = list(bytearray(struct.pack("<d", value)))
        if len(result) != 8:
            raise AssertionError(f"Float encoding produces incorrect format {result}")

        return result

    @classmethod
    def from_chunk(cls, pair, chunk) -> List:
        chunk = memoryview(chunk)
        if len(chunk) % TradeEntry.chunk_size:
            raise AssertionError(f"Incorrect chunk {chunk}")

        result = []
        for i in range(int(len(chunk) / TradeEntry.chunk_size)):
            start = i * TradeEntry.chunk_size
            result.append(TradeEntry(pair, chunk[start:start + TradeEntry.chunk_size]))

        return result
