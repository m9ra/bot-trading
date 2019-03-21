from typing import Any, List, Dict


class CurrencyPosition(object):
    def __init__(self, currency: str, position_data: List[Dict[str, Any]]):
        self.currency = currency
        self._buckets = list(position_data)

    @property
    def total_amount(self):
        return sum(bucket["amount"] for bucket in self._buckets)

    def get_amount_with(self, market, gain):
        accumulator = 0.0
        for bucket in self._buckets:
            amount = bucket["amount"]
            current_value = market.get_value(amount, self.currency)

            if current_value.amount >= bucket["initial_value"] * gain:
                accumulator += amount

        return accumulator

    def get_bucket_amounts_with(self, market, gain):
        result = []
        for bucket in self._buckets:
            amount = bucket["amount"]
            current_value = market.get_value(amount, self.currency)

            if current_value.amount >= bucket["initial_value"] * gain:
                result.append(amount)

        return result
