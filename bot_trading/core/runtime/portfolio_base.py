from typing import Dict

from bot_trading.core.runtime.transfer_command import TransferCommand


class PortfolioBase(object):
    def execute(self, command: TransferCommand) -> bool:
        raise NotImplementedError("has to be overridden")

    def get_state_copy(self) -> Dict:
        raise NotImplementedError("has to be overridden")
