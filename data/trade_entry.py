import struct


class TradeEntry(object):
    def __init__(self, pair: str, chunk):
        self.pair = pair
        self.price: float = None
        self.volume: float = None
        self.timestamp: float = None
        self.real_utc_timestamp: float = None

        # buy_byte + 8b price + 8b volume + 8b timestamp
        buy_byte, self.price, self.volume, self.timestamp = struct.unpack("<Bddd", chunk)

        if buy_byte <= 1:
            self.is_buy = buy_byte
            self.is_reset = False
        else:
            self.is_buy = buy_byte - 254
            self.is_reset = True
            self.real_utc_timestamp = self.timestamp
            self.timestamp = 0

        self.is_buy = bool(self.is_buy)

    def __repr__(self):

        mode = "buy" if self.is_buy else "sell"
        result = f"{self.timestamp} {self.pair} {mode} volume: {self.volume}, price: {self.price}"

        if self.is_reset:
            result = "reset " + result

        return result
