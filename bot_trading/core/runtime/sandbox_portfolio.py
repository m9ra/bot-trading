from copy import deepcopy
from typing import Dict

from bot_trading.core.runtime.portfolio_base import PortfolioBase
from bot_trading.trading.transfer_command import TransferCommand


class SandboxPortfolio(PortfolioBase):
    def __init__(self, market, portfolio_state: Dict):
        self._market = market
        self._current_state = deepcopy(portfolio_state)

    def execute(self, command: TransferCommand):
        command.apply(self._current_state, self._market)

    def get_state_copy(self):
        return deepcopy(self._current_state)
