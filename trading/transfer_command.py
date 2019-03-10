from trading.market import Market


class TransferCommand(object):
    def __init__(self, market: Market, source: str, source_amount: float, target: str, target_amount: float):
        self._market = market
        self._source = source
        self._source_amount = source_amount
        self._target = target
        self._target_amount = target_amount

    def apply(self, portfolio_state):
        # internal function that can be called only by the framework
        positions = portfolio_state["positions"]

        # subtract amount from positions
        # todo algorithm considering initial_value for bucket selection would be useful
        pending_amount = self._source_amount
        source_initial_value = self._market.get_value(self._source_amount, self._source).amount

        # get required amount from source buckets
        for source_bucket in positions[self._source]:
            amount = source_bucket["amount"]
            diff = min(amount, pending_amount)
            source_bucket["amount"] = amount - diff
            source_bucket["initial_value"] -= diff/self._source_amount * source_initial_value # proportional value
            pending_amount -= diff
            if pending_amount <= 0:
                break

        if pending_amount > 1e-9:
            raise ValueError(f"Missing {pending_amount}{self._source}.")

        # add amount to target bucket
        if self._target not in positions:
            positions[self._target] = []

        target_buckets = positions[self._target]
        if self._target == self._market.target_currency:
            target_bucket = target_buckets[0]
        else:
            target_buckets.append({"amount": 0, "initial_value": 0})
            target_bucket = target_buckets[-1]

        target_bucket["amount"] += self._target_amount
        target_bucket["initial_value"] += source_initial_value

        self._shrink(positions)

    def __repr__(self):
        return f"Transfer {self._source_amount}{self._source} --> {self._target_amount}{self._target}"

    def _shrink(self, positions):
        pass
