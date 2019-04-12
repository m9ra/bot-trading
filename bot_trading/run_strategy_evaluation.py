from bot_trading.bots.eva.optimizer import fast_backtest, load_samples
from bot_trading.bots.precalculated_strategy_bot import PrecalculatedStrategyBot
from bot_trading.bots.predictor_bot import PredictorBot
from bot_trading.bots.predictors.oraculum_predictor import OraculumPredictor

samples = load_samples("strategy_samples_1.bin")

# bot = PrecalculatedStrategyBot(samples)
# bot.import_strategy("strategy_1.bin")

from bot_trading.bots.neural_strategy_bot import NeuralStrategyBot

bot = NeuralStrategyBot()
bot.load("trained_models/ns_bot_4-12-04-11_30.bin", samples["data"].keys(), 0.5)
#bot = PredictorBot(OraculumPredictor())

fast_backtest(bot, samples)
"""
ORACULUM PREDICTOR BOT FINAL VALUE 1034.3219988453432 EUR
"""