from bot_trading.bots.baseline_bot import BaselineBot
from bot_trading.core.runtime.execution import run_real_trades

run_real_trades(BaselineBot())
