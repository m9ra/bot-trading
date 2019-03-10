from trading.portfolio_controller import PortfolioController


class BotBase(object):
    def __init__(self):
        self.update_interval = 10.0

    def update_portfolio(self, portfolio: PortfolioController):
        raise NotImplementedError("must be overridden")

