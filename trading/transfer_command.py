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
        # todo algorithm considering initial_value would be useful
        pending_amount = self._source_amount
        for position in positions[self._source]:
            amount = position["amount"]
            diff = min(amount, pending_amount)
            position["amount"] = amount - diff
            position["initial_value"] -= self._market.get_value(diff, self._source).amount
            pending_amount -= diff

            if pending_amount <= 0:
                break

        self._shrink(positions)

        if self._target not in positions:
            positions[self._target] = []

        target_positions = positions[self._target]

        if self._target == self._market.target_currency:
            position = target_positions[0]
        else:
            target_positions.append({"amount": 0, "initial_value": 0})
            position = target_positions[-1]

        position["amount"] += self._target_amount
        position["initial_value"] += self._market.get_value(self._target_amount, self._target).amount

    def __repr__(self):
        return f"Transfer {self._source_amount}{self._source} --> {self._target_amount}{self._target}"

    def _shrink(self, positions):
        pass
