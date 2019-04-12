from threading import Thread

from bot_trading.bots.bot_base import BotBase
from bot_trading.bots.eva import optimizer
from bot_trading.trading.portfolio_controller import PortfolioController


class EvaBot(BotBase):
    def __init__(self, bot):
        super().__init__()
        self._bot = bot

    def initialize(self, portfolio: PortfolioController):
        self._snapshot = portfolio.present

        self._eva()
        # self._thread = Thread(target=self._eva, daemon=True)
        # self._thread.start()

    def update_portfolio(self, portfolio: PortfolioController):
        pass  # todo let the best bot update the portfolio

    def _eva(self):
        optimizer.optimize(self._bot, self._snapshot, start_hours_ago=25, run_length_hours=3)
