class TransferCommand(object):
    def __init__(self, source: str, source_amount: float, target: str, target_amount: float):
        self._source = source
        self._source_amount = source_amount
        self._target = target
        self._target_amount = target_amount

    def apply(self, portfolio_state):
        # internal function that can be called only by the framework
        positions = portfolio_state["positions"]
        # todo subtract from buckets in a proper way
        positions[self._source][-1]["amount"] -= self._source_amount

        if self._target not in positions:
            positions[self._target] = []

        positions[self._target].append(
            {
                "amount": self._target_amount
            }
        )

    def __repr__(self):
        return f"Transfer {self._source_amount}{self._source} --> {self._target_amount}{self._target}"
