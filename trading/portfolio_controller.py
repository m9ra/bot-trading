from copy import deepcopy
from typing import Dict, Any, List

from trading.currency_history import CurrencyHistory
from trading.currency_position import CurrencyPosition
from trading.fund import Fund
from trading.transfer_command import TransferCommand


class PortfolioController(object):
    def __init__(self, market, portfolio_state: Dict[str, Any]):
        self._initial_portfolio_state = deepcopy(portfolio_state)

        self._currency_positions: Dict[str, CurrencyPosition] = {}
        self._commands = []
        self._market = market

        self._load_from_state(self._initial_portfolio_state)

    @property
    def total_value(self):
        present = self.present

        accumulator = Fund(0, self._market.target_currency)
        for fund in self.funds:
            accumulator += present.get_value(fund)

        return accumulator

    @property
    def currencies(self) -> List[str]:
        """ Currencies that can be traded."""
        return self._market.currencies

    @property
    def funds(self) -> List[Fund]:
        result = []
        for position in self._currency_positions.values():
            if position.total_amount > 0:
                result.append(Fund(position.total_amount, position.currency))

        return result

    @property
    def profitable_funds(self) -> List[Fund]:
        result = []
        for position in self._currency_positions.values():
            profitable_amount = position.get_profitable_amount(self._market)
            if profitable_amount > 0:
                result.append(Fund(profitable_amount, position.currency))

        return result

    @property
    def present(self) -> CurrencyHistory:
        return self.get_history(0)

    @property
    def target_currency(self):
        return self._market.target_currency

    def get_history(self, seconds_back) -> CurrencyHistory:
        return self._market.get_history(seconds_back)

    def request_conversion(self, source_fund: Fund, target_currency: str):
        """Requests transfer of amount of source_currency to the given target_currency"""
        self._validate_currencies(source_fund, target_currency)

        position = self._currency_positions.get(source_fund.currency)
        if position.total_amount < source_fund.amount:
            raise ValueError(
                f"Requested amount of {source_fund} is not available, only {position.total_amount}.")

        transfer_path = self._market.get_transfer_path(source_fund.currency, target_currency)

        present = self.present

        current_fund = source_fund
        for intermediate_currency in transfer_path[1:]:
            new_fund = present.after_conversion(current_fund, intermediate_currency)
            self.put_command(
                TransferCommand(self._market, current_fund.currency, current_fund.amount, new_fund.currency,
                                new_fund.amount))
            current_fund = new_fund

    def put_command(self, command):
        command.apply(self._current_portfolio_state)
        self._commands.append(command)

        self._load_from_state(self._current_portfolio_state)

    def reset_requests(self):
        """
        Resets portfolio to a state as it was when passed for trading to a bot.
        That means that all not committed commands will be reverted.
        """

        self._commands.clear()
        self._current_portfolio_state = deepcopy(self._initial_portfolio_state)
        self._load_from_state(self._current_portfolio_state)

    def _validate_currencies(self, *currencies):
        self._market.validate_currencies(*currencies)

    def _load_from_state(self, state: Dict[str, Any]):
        self._current_portfolio_state = deepcopy(state)

        self._currency_positions = {}
        for currency in self.currencies:
            position_data = self._current_portfolio_state.get("positions", {}).get(currency, [])
            self._currency_positions[currency] = CurrencyPosition(currency, position_data)
