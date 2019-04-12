from bot_trading.bots.predictor_bot import PredictorBot
from bot_trading.bots.predictors.neural_predictor import NeuralPredictor
from bot_trading.bots.scalping_bot import ScalpingBot
from bot_trading.core.runtime.execution import run_sandbox_trades, run_sandbox_backtest

# run_sandbox_trades(PredictorBot(NeuralPredictor(), prediction_lookahead=10),)


from bot_trading.bots.neural_strategy_bot import NeuralStrategyBot
from bot_trading.bots.eva.optimizer import load_samples

samples = load_samples("strategy_samples_1.bin")

bot = NeuralStrategyBot()
bot.load("trained_models/ns_bot_2-12-04-11_30.bin", samples["data"].keys(), 0.5)
run_sandbox_backtest(bot, start_hours_ago=5)
