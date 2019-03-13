from core.data.exceptions import TradeEntryNotAvailableException
from core.data.parsing import parse_pair
from trading.connector_base import ConnectorBase
from trading.fund import Fund
from trading.pricebook_view import PricebookView


class CurrencyHistory(object):
    def __init__(self, market: "Market", connector: ConnectorBase):
        self._market = market
        self._connector = connector
        self._current_time = None

    @property
    def currencies(self):
        return self._market.currencies

    @property
    def timestamp(self):
        return self._current_time

    @property
    def is_available(self):
        try:
            for pair in self._market.direct_currency_pairs:
                if not self._connector.get_pricebook(*parse_pair(pair), self._current_time).is_synchronized:
                    return False

        except TradeEntryNotAvailableException:
            return False

        return True

    def set_time(self, time: float):
        self._current_time = time

    def get_pricebook(self, source_currency: str, target_currency: str) -> PricebookView:
        return self._connector.get_pricebook(source_currency, target_currency, self._current_time)

    def get_unit_value(self, currency: str) -> float:
        return self.get_value(Fund(1.0, currency)).amount

    def get_value(self, fund: Fund) -> Fund:
        return self.after_conversion(fund, self._market.target_currency)

    def after_conversion(self, fund: Fund, currency: str) -> Fund:
        path = self._market.get_transfer_path(fund.currency, currency)

        current_fund = fund
        for intermediate_currency in path[1:]:
            pricebook = self.get_pricebook(current_fund.currency, intermediate_currency)
            current_fund = pricebook.after_conversion(current_fund)

        return current_fund
