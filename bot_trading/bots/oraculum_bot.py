from bot_trading.bots.bot_base import BotBase
from bot_trading.trading.portfolio_controller import PortfolioController
from bot_trading.trading.utils import future_value


class OraculumBot(BotBase):
    def update_portfolio(self, portfolio: PortfolioController):
        """
        This bot is used for market efficiency estimation.
        """
        now = portfolio.get_history(seconds_back=0)
        future = portfolio.get_history(seconds_back=-self.update_interval)

        for fund in portfolio.funds:
            best_currency = max(portfolio.currencies, key=lambda currency: future_value(fund, currency, now, future))
            if best_currency != fund.currency:
                portfolio.request_transfer(fund, best_currency)
