from data.trade_entry import TradeEntry
from trading.pricebook_view import PricebookView


class ConnectorBase(object):
    def get_pricebook(self, source_currency: str, target_currency: str, time: float) -> PricebookView:
        raise NotImplementedError()

    def next_entry(self) -> TradeEntry:
        raise NotImplementedError("must be overridden")

    def is_synchronized(self, pair, time: float):
        raise NotImplementedError("must be overriden")
