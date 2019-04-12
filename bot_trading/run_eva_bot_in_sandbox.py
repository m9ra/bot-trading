from bot_trading.bots.eva.eva_bot import EvaBot
from bot_trading.bots.oraculum_bot import OraculumBot
from bot_trading.bots.predictor_bot import PredictorBot
from bot_trading.bots.predictors.linear_predictor import LinearPredictor
from bot_trading.bots.predictors.neural_predictor import NeuralPredictor
from bot_trading.bots.scalping_bot import ScalpingBot
from bot_trading.core.runtime.execution import run_sandbox_trades

bot = EvaBot(
    PredictorBot(NeuralPredictor(), prediction_lookahead=10)
)
run_sandbox_trades(bot)
