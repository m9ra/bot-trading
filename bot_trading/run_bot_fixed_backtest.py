from bot_trading.bots.eva.eva_bot import EvaBot
from bot_trading.bots.oraculum_bot import OraculumBot
from bot_trading.bots.predictor_bot import PredictorBot
from bot_trading.bots.predictors.linear_predictor import LinearPredictor
from bot_trading.bots.predictors.neural_predictor import NeuralPredictor
from bot_trading.bots.predictors.oraculum_predictor import OraculumPredictor
from bot_trading.bots.scalping_bot import ScalpingBot
from bot_trading.core.runtime.execution import run_sandbox_backtest

run_sandbox_backtest(
    PredictorBot(NeuralPredictor("m11_current"), prediction_lookahead=10),
    #EvaBot(PredictorBot(LinearPredictor(1))),
    #PredictorBot(OraculumPredictor()),

    start_timestamp=1554495398.6071417,
    run_length_in_hours=12.0

    #start_hours_ago=20,
)

""" Neuro - no sampling, relu
FINAL PORTFOLIO: Total value: 980.9663987958627 EUR || Funds: [636.163018127773 XRP, 581.1139929290498 EUR, 1793.7219730941704 XLM]
EXECUTION WALLTIME: 1157.7888514995575 seconds
"""

""" Oraculum bot
FINAL PORTFOLIO: Total value: 1141.0757127858242 EUR || Funds: [10233.771112239569 XLM]
EXECUTION WALLTIME: 159.78130531311035 seconds
"""