from typing import Dict

from bot_trading.trading.transfer_command import TransferCommand


class PortfolioBase(object):
    def execute(self, command: TransferCommand):
        raise NotImplementedError("has to be overridden")

    def get_state_copy(self) -> Dict:
        raise NotImplementedError("has to be overridden")
