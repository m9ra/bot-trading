class TradeEntryNotAvailableException(Exception):
    def __init__(self, pair: str, timestamp: float = None, entry_index: int = None):
        super().__init__(f"Requested entry is not available for {pair} at {entry_index} on {timestamp}")


class PortfolioUpdateException(Exception):
    def __init__(self, message):
        super().__init__(message)
