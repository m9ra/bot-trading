from bot_trading.bots.scalping_bot import ScalpingBot
from bot_trading.core.runtime.execution import run_sandbox_trades

run_sandbox_trades(ScalpingBot())
