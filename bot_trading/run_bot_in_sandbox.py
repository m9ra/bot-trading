from bot_trading.bots.complex_baseline_bot import ComplexBaselineBot
from bot_trading.core.runtime.execution import run_sandbox_trades

run_sandbox_trades(ComplexBaselineBot())
