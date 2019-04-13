from typing import List, Tuple

from bot_trading.core.exceptions import TradeEntryNotAvailableException
from bot_trading.core.data.parsing import parse_pair
from bot_trading.core.runtime.connector_base import ConnectorBase
from bot_trading.trading.fund import Fund
from bot_trading.trading.pricebook_view import PricebookView


class PriceSnapshot(object):
    def __init__(self, market: "Market", connector: ConnectorBase, current_time: float):
        self._market = market
        self._connector = connector
        self._current_time = current_time

    @property
    def currencies(self):
        return self._market.currencies

    @property
    def target_currency(self):
        return self._market.target_currency

    @property
    def non_target_currencies(self):
        return self._market.non_target_currencies

    @property
    def timestamp(self):
        return self._current_time

    @property
    def is_available(self):
        """
        Determine whether the snasphot is available for all traded pairs.
        It can happen that when too far history is requested, some of the pair data won't be available.
        """

        try:
            for pair in self._market.direct_currency_pairs:
                if not self._connector.get_pricebook(*parse_pair(pair), self._current_time).is_synchronized:
                    return False

        except TradeEntryNotAvailableException:
            return False

        return True

    def get_pricebook(self, source_currency: str, target_currency: str) -> PricebookView:
        return self._connector.get_pricebook(source_currency, target_currency, self._current_time)

    def get_snapshot(self, seconds_back):
        return PriceSnapshot(self._market, self._connector, self._current_time - seconds_back)

    def get_unit_value(self, currency: str) -> float:
        return self.get_value(Fund(1.0, currency)).amount

    def get_unit_cost(self, currency: str) -> float:
        return self.get_cost(Fund(1.0, currency)).amount

    def get_value(self, fund: Fund) -> Fund:
        return self.after_conversion(fund, self._market.target_currency)

    def get_cost(self, fund: Fund) -> Fund:
        return self.to_convert(self._market.target_currency, fund)

    def after_conversion(self, fund: Fund, currency: str) -> Fund:
        path = self._market.get_transfer_path(fund.currency, currency)

        current_fund = fund
        for intermediate_currency in path[1:]:
            pricebook = self.get_pricebook(current_fund.currency, intermediate_currency)
            current_fund = pricebook.after_conversion(current_fund)

        return current_fund

    def to_convert(self, currency: str, fund: Fund) -> Fund:
        path = self._market.get_transfer_path(fund.currency, currency)

        current_fund = fund
        for intermediate_currency in path[1:]:
            pricebook = self.get_pricebook(current_fund.currency, intermediate_currency)
            current_fund = pricebook.to_convert(current_fund)

        return current_fund

    def get_spread(self, currency: str) -> float:
        pricebook = self.get_pricebook(currency, self._market.target_currency)
        return pricebook.spread

    def get_unit_value_samples(self, currency: str, sampling_period: float, end_timestamp: float = None) -> List[float]:
        pricebook = self.get_pricebook(currency, self._market.target_currency)

        result = []

        end_timestamp = end_timestamp or self._market.current_time
        current_time = self._current_time
        while current_time <= end_timestamp:
            pricebook.fast_forward_to(current_time)
            result.append(pricebook.bid_ask[0])
            current_time += sampling_period

        return result

    def get_unit_bid_ask_samples(self, currency: str, sampling_period: float, end_timestamp: float = None) -> List[
        Tuple[float, float]]:
        pricebook = self.get_pricebook(currency, self._market.target_currency)

        result = []

        end_timestamp = end_timestamp or self._market.current_time
        current_time = self._current_time
        while current_time <= end_timestamp:
            pricebook.fast_forward_to(current_time)
            result.append(pricebook.bid_ask)
            current_time += sampling_period

        return result
