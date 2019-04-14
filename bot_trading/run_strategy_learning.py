from bot_trading.bots.eva.optimizer import load_samples, fast_backtest
from bot_trading.bots.precalculated_strategy_bot import PrecalculatedStrategyBot
from bot_trading.bots.neural_strategy_bot import NeuralStrategyBot

samples = load_samples("strategy_samples_12-04-11_30.bin")
validation_samples = load_samples("strategy_samples_1.bin")

bot = PrecalculatedStrategyBot(samples)
bot.import_strategy("strategy_2-12-04-11_30.bin")

strategy = bot.get_strategy_copy()


def real_run_validator():
    return -fast_backtest(bot, validation_samples)


bot = NeuralStrategyBot()
bot.fit(samples, strategy, file_path="trained_models/ns_bot_8b.bin", validator=real_run_validator)
