class Fund(object):
    def __init__(self, amount: float, currency: str):
        self._amount = amount
        self._currency = currency

    @property
    def amount(self):
        return self._amount

    @property
    def currency(self):
        return self._currency

    def __repr__(self):
        return f"{self.amount} {self._currency}"

    def __truediv__(self, other):
        return Fund(self._amount / other, self._currency)

    def __add__(self, other):
        if other == 0.0 or other == 0:
            return self

        if not isinstance(other, Fund):
            raise ValueError(f"Incompatible operatoin {self} + {other}")

        if self._currency != other._currency:
            raise ValueError(f"Incompatible operation {self} + {other}")

        return Fund(self._amount + other._amount, self._currency)
