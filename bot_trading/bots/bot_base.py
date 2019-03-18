from bot_trading.core.runtime.portfolio_base import PortfolioBase
from bot_trading.trading.portfolio_controller import PortfolioController


class BotBase(object):
    def __init__(self):
        self.update_interval = 10.0
        self.portfolio_connector: PortfolioBase = None

    def update_portfolio(self, portfolio: PortfolioController):
        raise NotImplementedError("must be overridden")
