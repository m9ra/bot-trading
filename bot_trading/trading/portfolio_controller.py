from copy import deepcopy
from typing import Dict, Any, List, Optional

from bot_trading.trading.currency_history import CurrencyHistory
from bot_trading.trading.currency_position import CurrencyPosition
from bot_trading.trading.fund import Fund
from bot_trading.trading.market import Market
from bot_trading.core.runtime.transfer_command import TransferCommand


class PortfolioController(object):
    def __init__(self, market: Market, portfolio_state: Dict[str, Any]):
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
    def non_target_currencies(self) -> List[str]:
        currencies = list(self._market.currencies)
        currencies.remove(self.target_currency)
        return currencies

    @property
    def pairs(self):
        return self._market.direct_currency_pairs

    @property
    def funds(self) -> List[Fund]:
        result = []
        for position in self._currency_positions.values():
            if position.total_amount > 0:
                result.append(Fund(position.total_amount, position.currency))

        return result

    @property
    def profitable_funds(self) -> List[Fund]:
        return self.get_funds_with(gain_greater_than=1.0)

    @property
    def present(self) -> CurrencyHistory:
        return self.get_history(0)

    @property
    def target_currency(self):
        return self._market.target_currency

    def get_history(self, seconds_back) -> CurrencyHistory:
        return self._market.get_history(seconds_back)

    def request_transfer(self, source_fund: Fund, target_currency: str, allowed_loss_ratio=0.0001):
        """Requests transfer of amount of source_currency to the given target_currency"""
        for command in self.create_transfer_commands(source_fund, target_currency, allowed_loss_ratio):
            self.put_command(command)

    def create_transfer_commands(self, source_fund: Fund, target_currency: str, allowed_loss_ratio=0.0001):
        self._validate_currencies(source_fund, target_currency)

        position = self._currency_positions.get(source_fund.currency)
        if position.total_amount < source_fund.amount:
            raise ValueError(
                f"Requested amount of {source_fund} is not available, only {position.total_amount}.")

        transfer_path = self._market.get_transfer_path(source_fund.currency, target_currency)

        present = self.present

        result_commands = []
        current_fund = source_fund
        for intermediate_currency in transfer_path[1:]:
            new_fund = present.after_conversion(current_fund, intermediate_currency)
            result_commands.append(
                TransferCommand(current_fund.currency, current_fund.amount, new_fund.currency,
                                new_fund.amount * (1 - allowed_loss_ratio)))
            current_fund = new_fund

        return result_commands

    def put_command(self, command):
        command.apply(self._current_portfolio_state, self._market)
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

    def get_funds_with(self, gain_greater_than: float, force_include_target: bool = True) -> List[Fund]:
        result = []
        for position in self._currency_positions.values():
            if position.currency == self.target_currency and force_include_target:
                if position.total_amount > 0:
                    result.append(Fund(position.total_amount, position.currency))
                continue

            for bucket_amount in position.get_bucket_amounts_with(self._market, gain_greater_than):
                if bucket_amount > 0:
                    result.append(Fund(bucket_amount, position.currency))

        return result

    def get_fund_with(self, currency, gain_greater_than: float, force_include_target=True) -> Optional[Fund]:
        if currency == self.target_currency and force_include_target:
            return Fund(self._currency_positions[currency].total_amount, currency)

        profitable_amount = self._currency_positions[currency].get_amount_with(self._market, gain_greater_than)
        if profitable_amount > 0:
            return Fund(profitable_amount, currency)

        return None

    def get_funds(self, currency):
        result = []
        for amount in self._currency_positions[currency].get_bucket_amounts():
            result.append(Fund(amount, currency))

        return result

    def can_sell(self, amount, currency):
        available_amount = sum(f.amount for f in self.get_funds(currency))
        return available_amount > amount

    def print_pricebook_info(self, source_currency, target_currency):
        pricebook = self.present.get_pricebook(source_currency, target_currency)

        print("SELL")
        for level in pricebook.sell_levels:
            print(level)

        print()
        print("BUY")
        for level in pricebook.buy_levels:
            print(level)

        print("\n\n\n")

    def __repr__(self):
        return f"Total value: {self.total_value} || Funds: {self.funds}"

    def _validate_currencies(self, *currencies):
        self._market.validate_currencies(*currencies)

    def _load_from_state(self, state: Dict[str, Any]):
        self._current_portfolio_state = deepcopy(state)

        self._currency_positions = {}
        for currency in self.currencies:
            position_data = self._current_portfolio_state.get("positions", {}).get(currency, [])
            self._currency_positions[currency] = CurrencyPosition(currency, position_data)
