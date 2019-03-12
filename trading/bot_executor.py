import time

from bots.bot_base import BotBase
from data.storage_reader import TradeEntry
from trading.market import Market
from trading.portfolio_controller import PortfolioController


class BotExecutor(object):
    def __init__(self, bot: BotBase, market: Market, initial_value: float):
        self._bot = bot
        self._market = market
        self._portfolio_state = {
            "positions": {
                market.target_currency: [
                    {
                        "amount": initial_value,
                        "initial_value": initial_value
                    }
                ]
            }
        }

        self._current_time = 0.0
        self._bot_slack = 0.0  # compensates for bot calculation time
        self._last_bot_update = 0
        self._is_synchronized = False

    def run(self):
        self._market.subscribe(self)
        self._market.run()

    def receive(self, entry: TradeEntry):
        print(".", end="", flush=True)
        self._register(self._market.current_time)

    def _register(self, timestamp):
        self._update_slack(timestamp)
        if self._bot_slack > 0:
            return  # bot can't trade (its in time slack or not enough info was collected yet)

        if not self._is_synchronized and self._market.get_history(0).is_available:
            # once the present is available, the executor got synchronized
            self._is_synchronized = True

        if self._current_time - self._last_bot_update >= self._bot.update_interval:
            self._consult_bot()
            self._last_bot_update = self._current_time

    def _consult_bot(self):
        print(self._current_time)

        start = time.time()
        portfolio = PortfolioController(self._market, self._portfolio_state)
        print(portfolio)
        value_before = portfolio.total_value
        self._bot.update_portfolio(portfolio)
        end = time.time()

        # compensate for bot calculation time
        self._bot_slack += end - start

        if not portfolio._commands:
            return

        print(f"\nPortfolio value before: {value_before}")
        for command in portfolio._commands:
            print(f"\t{command}")
            command.apply(self._portfolio_state)

        print(f"Portfolio value after: {portfolio.total_value}\n")

    def _update_slack(self, new_time):
        # sync time with the bot execution delay

        last_time = self._current_time
        self._current_time = max(self._current_time, new_time)
        sync_time = self._current_time - last_time
        self._bot_slack = max(0, self._bot_slack - sync_time)
