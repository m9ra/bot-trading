from bot_trading.bots.oraculum_bot import OraculumBot
from bot_trading.bots.predictor_bot import PredictorBot
from bot_trading.bots.predictors.linear_predictor import LinearPredictor
from bot_trading.bots.predictors.neural_predictor import NeuralPredictor
from bot_trading.bots.scalping_bot import ScalpingBot
from bot_trading.core.runtime.execution import run_sandbox_backtest

"""
If you don't want to install tensorflow, tflearn, numpy... than remove NeuralPredictor from imports and the code below.
"""

run_sandbox_backtest(
    ## Uncomment following lines (one at a time), to try out different bots
    # PredictorBot(LinearPredictor(delta_scale=0.5)),
    PredictorBot(NeuralPredictor(), prediction_lookahead=10),
    # OraculumBot(),
    # ScalpingBot(),

    ## Specify historic area where to run the backtest
    start_hours_ago=4.0,  # comment out to run from beginning of the available history
    # run_length_in_hours=0.5 # comment out to run until present
)
