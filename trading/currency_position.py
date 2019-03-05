from typing import Any, List, Dict


class CurrencyPosition(object):
    def __init__(self, currency:str, position_data: List[Dict[str, Any]]):
        self.currency = currency
        self._buckets = list(position_data)

    @property
    def total_amount(self):
        return sum(bucket["amount"] for bucket in self._buckets)
