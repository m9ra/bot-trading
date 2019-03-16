import sys
import time

from bot_trading.bots.bot_base import BotBase
from bot_trading.configuration import TARGET_CURRENCY, TRADING_ENDPOINT, INITIAL_AMOUNT
from bot_trading.core.networking.remote_observer import RemoteObserver
from bot_trading.core.runtime.remote_portfolio import RemotePortfolio
from bot_trading.core.runtime.sandbox_portfolio import SandboxPortfolio
from bot_trading.core.runtime.validation import validate_email
from bot_trading.trading.bot_executor import BotExecutor
from bot_trading.trading.fullpass_connector import FullpassConnector
from bot_trading.trading.market import Market
from bot_trading.trading.peek_connector import PeekConnector


def run_sandbox_trades(bot: BotBase):
    market, _ = create_trading_env()
    portfolio = SandboxPortfolio(market, get_initial_portfolio_state())
    run_on_market(market, bot, portfolio)


def run_real_trades(bot: BotBase):
    market, observer = create_trading_env()
    portfolio = RemotePortfolio(observer)
    run_on_market(market, bot, portfolio)


def run_on_market(market, bot, portfolio):
    executor = BotExecutor(bot, market, portfolio)
    start = time.time()
    executor.run()
    end = time.time()
    print()
    print(f"RUN DURATION: {end - start} seconds")


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


def create_trading_env():
    HISTORY_MODE = "history"
    PEEK_MODE = "peek"

    if len(sys.argv) != 3:
        raise ValueError(f"Expecting command arguments: [{HISTORY_MODE}|{PEEK_MODE}] [username@is.email]")

    connector_mode = sys.argv[1]
    username = sys.argv[2]

    if connector_mode not in [HISTORY_MODE, PEEK_MODE]:
        raise ValueError(f"Invalid connector mode {connector_mode}")

    validate_email(username)

    observer = RemoteObserver(TRADING_ENDPOINT, username, "no_password_yet")
    observer.connect()

    readers = observer.get_readers()
    market_pairs = observer.get_pairs()

    if connector_mode == PEEK_MODE:
        connector = PeekConnector(readers)
    elif connector_mode == HISTORY_MODE:
        connector = FullpassConnector(readers)
    else:
        raise ValueError(f"Unknown connector mode {connector_mode}. Can be peek or full")

    return Market(TARGET_CURRENCY, market_pairs, connector), observer
