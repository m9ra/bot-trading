from bot_trading.bots.manual_bot.interface import ManualBot
from bot_trading.core.runtime.execution import run_real_trades

run_real_trades(ManualBot(web_port=5522))
