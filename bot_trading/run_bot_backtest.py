from bot_trading.bots.scalping_bot import ScalpingBot
from bot_trading.core.runtime.execution import run_sandbox_backtest

run_sandbox_backtest(
    ScalpingBot(),
    start_hours_ago=10.0,
    #run_duration_hours=0.5
)
