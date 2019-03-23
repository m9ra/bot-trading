import os
import time

from bot_trading.bots.bot_base import BotBase
from bot_trading.core.configuration import INITIAL_AMOUNT, TARGET_CURRENCY
from bot_trading.core.networking.remote_observer import RemoteObserver
from bot_trading.core.runtime.remote_portfolio import RemotePortfolio
from bot_trading.core.runtime.sandbox_portfolio import SandboxPortfolio
from bot_trading.core.runtime.validation import validate_email
from bot_trading.trading.bot_executor import BotExecutor
from bot_trading.core.runtime.fullpass_connector import FullpassConnector
from bot_trading.core.runtime.market import Market
from bot_trading.core.runtime.peek_connector import PeekConnector
from bot_trading.trading.portfolio_controller import PortfolioController

HISTORY_MODE = "history"
PEEK_MODE = "peek"

WRITE_MODE = "write"
READ_MODE = "read"


def get_username():
    from bot_trading.configuration import USERNAME
    username = os.getenv("USERNAME", USERNAME)

    return username


def run_sandbox_trades(bot: BotBase):
    market, _ = create_trading_env(PEEK_MODE, READ_MODE)
    portfolio = SandboxPortfolio(market, get_initial_portfolio_state())
    run_on_market(market, bot, portfolio)


def run_sandbox_backtest(bot: BotBase, start_hours_ago=None, run_duration_hours=None,
                         start_timestamp=None, end_timestamp=None):
    market, _ = create_trading_env(HISTORY_MODE, READ_MODE)

    if start_timestamp and start_hours_ago:
        raise ValueError("Only one of start_timestamp and start_hours_ago can be specified")

    if end_timestamp and run_duration_hours:
        raise ValueError("Only one of end_timestamp and run_duration_hours can be specified")

    if start_hours_ago != None:
        start_timestamp = time.time() - start_hours_ago * 3600

    if start_timestamp:
        market._connector.set_run_start(start_timestamp)

    if run_duration_hours:
        start = market._connector.get_start_timestamp()
        end_timestamp = start + run_duration_hours * 3600

    if end_timestamp:
        market._connector.set_run_end(end_timestamp)

    portfolio = SandboxPortfolio(market, get_initial_portfolio_state())
    run_on_market(market, bot, portfolio)


def run_real_trades(bot: BotBase):
    market, observer = create_trading_env(PEEK_MODE, WRITE_MODE)
    portfolio = RemotePortfolio(observer)
    run_on_market(market, bot, portfolio)


def run_on_market(market, bot, portfolio):
    executor = BotExecutor(bot, market, portfolio)
    start = time.time()
    executor.run()
    end = time.time()
    print()
    portfolio = PortfolioController(market, portfolio.get_state_copy())
    print(f"FINAL PORTFOLIO: {portfolio}")
    print(f"EXECUTION WALLTIME: {end - start} seconds")


def get_initial_portfolio_state():
    return {
        "positions": {
            TARGET_CURRENCY: [
                {
                    "amount": INITIAL_AMOUNT,
                    "initial_value": INITIAL_AMOUNT
                }
            ]
        }
    }


def create_trading_env(connector_mode, access_mode):
    from bot_trading.configuration import TRADING_ENDPOINT

    username = get_username()
    validate_email(username)

    if connector_mode not in [HISTORY_MODE, PEEK_MODE]:
        raise ValueError(f"Invalid connector mode {connector_mode}")

    if access_mode not in [READ_MODE, WRITE_MODE]:
        raise ValueError(f"Invalid access mode {access_mode}")

    print(f"CONNECTING TO {TRADING_ENDPOINT}")
    observer = RemoteObserver(TRADING_ENDPOINT, username, "no_password_yet")
    observer.connect(access_mode)

    readers = observer.get_readers()
    market_pairs = observer.get_pairs()

    if connector_mode == PEEK_MODE:
        connector = PeekConnector(readers)
    elif connector_mode == HISTORY_MODE:
        connector = FullpassConnector(readers)
    else:
        raise ValueError(f"Unknown connector mode {connector_mode}. Can be peek or full")

    return Market(TARGET_CURRENCY, market_pairs, connector), observer
