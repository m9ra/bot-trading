from typing import Dict, Tuple, List

from bot_trading.core.runtime.execution import create_trading_env, WRITE_MODE, HISTORY_MODE, PEEK_MODE

# THOSE OBJECTS EXPOSE API TO THE REMOTE SERVER
from bot_trading.trading.pricebook_view import PricebookView

market, observer = create_trading_env(PEEK_MODE, WRITE_MODE)
market.run_async()


# ========== API USAGE EXAMPLES =========

def get_bid_ask_samples(seconds_back: float, duration: float = float("inf"), period=1.0) -> \
        Dict[str, List[Tuple[float, float, float]]]:
    """
    For each non-target currency returns triplets of (timestamp, bid, ask)
    sampled every period of the specified time interval.
    """

    samples = {}
    history = market.get_history(seconds_back)

    for currency in market.non_target_currencies:
        # collect samples from pricebook view which starts at the specified history
        pricebook: PricebookView = history.get_pricebook(currency, market.target_currency)

        samples[currency] = currency_samples = []
        current_time = history.timestamp
        end_time = current_time + duration
        while current_time < end_time:
            # start collecting the data
            bid, ask = pricebook.bid_ask
            currency_samples.append((current_time, bid, ask))

            current_time += period
            # shift to next period
            if not pricebook.fast_forward_to(current_time):
                break  # end early if no more data are not available

    return samples


print(get_bid_ask_samples(100, period=10.0))
