from bot_trading.bots.predictor_bot import PredictorBot
from bot_trading.bots.predictors.neural_predictor import NeuralPredictor
from bot_trading.bots.scalping_bot import ScalpingBot
from bot_trading.core.runtime.execution import run_real_trades

run_real_trades(PredictorBot(NeuralPredictor(), prediction_lookahead=10))
