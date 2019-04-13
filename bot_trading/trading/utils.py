import datetime
from typing import Dict

from bot_trading.trading.price_snapshot import PriceSnapshot
from bot_trading.trading.fund import Fund
from bot_trading.trading.portfolio_controller import PortfolioController


def calculate_value_deltas(present: PriceSnapshot, history: PriceSnapshot) -> Dict[str, float]:
    result = {}
    for currency in present.currencies:
        price_delta = present.get_unit_value(currency) - history.get_unit_value(currency)
        result[currency] = price_delta

    return result


def filter_currencies(deltas: Dict[str, float], portfolio: PortfolioController, gain,
                      force_include_target_currency=True):
    result = {}

    for currency, delta in deltas.items():
        current_gain = 1.0 if force_include_target_currency and currency == portfolio.target_currency else gain
        fund = portfolio.get_fund_with(currency, current_gain)
        if fund and fund.amount > 0:
            result[currency] = delta

    return result


def future_value(fund: Fund, target_currency: str, present: PriceSnapshot, future):
    converted_fund = present.after_conversion(fund, target_currency)
    #if converted_fund.currency != target_currency:
    #    converted_fund = Fund(converted_fund.amount * 0.99, converted_fund.currency)

    value = future.get_value(converted_fund)
    #print(f"{converted_fund} value estimation: {value}")

    return value


def timestamp_to_datetime(timestamp):
    return datetime.datetime.fromtimestamp(timestamp)
