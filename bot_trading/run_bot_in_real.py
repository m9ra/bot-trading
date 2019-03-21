from bot_trading.bots.scalping_bot import ScalpingBot
from bot_trading.core.runtime.execution import run_real_trades

run_real_trades(ScalpingBot())
