from copy import deepcopy

from bot_trading.core.messages import log_command
from bot_trading.core.networking.remote_observer import RemoteObserver
from bot_trading.core.runtime.portfolio_base import PortfolioBase


class RemotePortfolio(PortfolioBase):
    def __init__(self, remote_observer: RemoteObserver):
        self._remote_observer = remote_observer
        self._current_state = None

    def execute(self, command):
        response = self._remote_observer.send_portfolio_command_request(command)

        if not response or not response.get("accepted"):
            log_command(f"\t declined: {command}")
            return

        self._current_state = response["portfolio_state"]

    def get_state_copy(self):
        if self._current_state is None:
            self._current_state = self._remote_observer.receive_portfolio_state()

        return deepcopy(self._current_state)
