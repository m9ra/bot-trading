from bot_trading.bots.baseline_bot import BaselineBot
from bot_trading.core.runtime.execution import run_sandbox_trades

run_sandbox_trades(BaselineBot())
