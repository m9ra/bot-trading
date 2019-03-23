from bot_trading.core.runtime.portfolio_base import PortfolioBase
from bot_trading.trading.portfolio_controller import PortfolioController


class BotBase(object):
    def __init__(self):
        self.update_interval = 10.0
        self.portfolio_connector: PortfolioBase = None

        self._is_initialized = False

    def initialize(self, portfolio: PortfolioController):
        """
        Is called for the first time when portfolio.present.is_available
        """
        pass  # by default nothing to do here

    def update_portfolio(self, portfolio: PortfolioController):
        """
        Is called once in an update interval and is responsible for updating the portfolio (i.e. issuing transfers)
        """
        raise NotImplementedError("must be overridden")

    def ensure_initialization(self, portfolio: PortfolioController):
        """
        Ensures that bot will be initialized (exactly once)
        """
        if self._is_initialized:
            return  # bot is initialized already

        self._is_initialized = True
        self.initialize(portfolio)
