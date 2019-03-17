import time
import datetime

from bot_trading.bots.bot_base import BotBase
from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.core.messages import log_executor, log_portfolio, log_command
from bot_trading.core.runtime.portfolio_base import PortfolioBase
from bot_trading.trading.market import Market
from bot_trading.trading.portfolio_controller import PortfolioController


class BotExecutor(object):
    def __init__(self, bot: BotBase, market: Market, portfolio: PortfolioBase):
        self._bot = bot
        self._market = market
        self._portfolio = portfolio

        self._current_time = 0.0
        self._bot_slack = 0.0  # compensates for bot calculation time
        self._last_bot_update = 0
        self._is_synchronized = False

    def run(self):
        try:
            self._market.subscribe(self)
            self._market.run()
        except KeyboardInterrupt:
            print()
            print("EXECUTOR IS STOPPING")

    def receive(self, entry: TradeEntry):
        log_executor(f"\r......[MARKET_CLOCK] {datetime.datetime.fromtimestamp(self._current_time)}", end=" " * 5,
                     flush=True)
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
        log_executor(f"\r[MARKET_CLOCK] {datetime.datetime.fromtimestamp(self._current_time)}", end=" " * 30 + "\n")

        start = time.time()
        portfolio = PortfolioController(self._market, self._portfolio.get_state_copy())
        log_portfolio(portfolio)
        value_before = portfolio.total_value
        self._bot.update_portfolio(portfolio)
        end = time.time()

        # compensate for bot calculation time
        self._bot_slack += end - start

        if not portfolio._commands:
            return

        log_command(f"Portfolio value before: {value_before}")
        for command in portfolio._commands:
            log_command(f"\t {command}")
            self._portfolio.execute(command)

        portfolio._load_from_state(self._portfolio.get_state_copy())
        after_value = portfolio.total_value
        log_command(f"Portfolio value after: {after_value}\n")

    def _update_slack(self, new_time):
        # sync time with the bot execution delay

        last_time = self._current_time
        self._current_time = max(self._current_time, new_time)
        sync_time = self._current_time - last_time
        self._bot_slack = max(0, self._bot_slack - sync_time)
