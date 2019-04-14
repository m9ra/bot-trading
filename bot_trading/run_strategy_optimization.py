import os
import pickle

from bot_trading.bots.eva.optimizer import optimize_with_samples, save_samples, load_samples
from bot_trading.bots.precalculated_strategy_bot import PrecalculatedStrategyBot
from bot_trading.core.runtime.execution import create_trading_env, READ_MODE, PEEK_MODE

market, observer = create_trading_env(PEEK_MODE, READ_MODE)
market.run_async()

SAMPLE_FILE = "data_13-04-20_00.bin"
# SAMPLE_FILE = "strategy_samples_1.bin"
SAMPLING_PERIOD = 0.5


def main():
    samples = load_samples(SAMPLE_FILE)
    if not samples:
        print("CREATING SAMPLES")
        # samples = create_samples(1554495398.6071417+12.0*3600, length_in_hours=12.0, period_in_seconds=SAMPLING_PERIOD)
        samples_length_in_hours = 2.0 * 168.0
        samples = create_samples(
            1555179300 - samples_length_in_hours * 3600,
            length_in_hours=samples_length_in_hours,
            period_in_seconds=SAMPLING_PERIOD
        )
        save_samples(SAMPLE_FILE, samples)

    bot = PrecalculatedStrategyBot(samples)
    bot.calculate_strategy()
    bot.export_strategy("strategy_2-12-04-11_30.bin")
    # return

    bot.plot()
    print("Optimization starts")
    optimize_with_samples(bot, samples, samples["meta"]["length_in_hours"], market.present)


def create_samples(end_timestamp, length_in_hours, period_in_seconds):
    seconds_back = market.current_time - end_timestamp + length_in_hours * 3600
    snapshot = market.get_history(seconds_back)

    data = {}
    samples = {
        "meta": {
            "end_timestamp": end_timestamp,
            "length_in_hours": length_in_hours,
            "period_in_seconds": period_in_seconds
        },
        "data": data
    }

    for currency in snapshot.non_target_currencies:
        data[currency] = snapshot.get_unit_bid_ask_samples(currency, sampling_period=period_in_seconds,
                                                           end_timestamp=end_timestamp)

    return samples


main()
