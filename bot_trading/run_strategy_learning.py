from bot_trading.bots.eva.optimizer import load_samples
from bot_trading.bots.precalculated_strategy_bot import PrecalculatedStrategyBot
from bot_trading.bots.neural_strategy_bot import NeuralStrategyBot

samples = load_samples("strategy_samples_12-04-11_30.bin")
bot = PrecalculatedStrategyBot(samples)
bot.import_strategy("strategy_1-12-04-11_30.bin")

strategy = bot.get_strategy_copy()

bot = NeuralStrategyBot()
bot.fit(samples, strategy, file_path="trained_models/ns_bot_6-12-04-11_30.bin")
