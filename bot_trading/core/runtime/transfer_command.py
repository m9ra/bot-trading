import operator
from bot_trading.configuration import DUST_LEVEL, MIN_POSITION_BUCKET_VALUE
from bot_trading.core.exceptions import PortfolioUpdateException
from bot_trading.trading.fund import Fund
from bot_trading.trading.market import Market


class TransferCommand(object):
    def __init__(self, source: str, source_amount: float, target: str, min_target_amount: float):
        self._source = source
        self._source_amount = source_amount
        self._target = target
        self._min_target_amount = min_target_amount

    def apply(self, portfolio_state, market: Market):
        if self._source_amount <= DUST_LEVEL:
            raise PortfolioUpdateException(f"Requested source amount {self._source_amount} is too low.")

        target_amount = market.present.after_conversion(Fund(self._source_amount, self._source), self._target).amount
        if target_amount < self._min_target_amount:
            # the real target amount is not meeting the expectations
            raise PortfolioUpdateException(
                f"Requested {self._min_target_amount} but got only {target_amount} of {self._target}")

        positions = portfolio_state["positions"]

        # subtract amount from source positions
        pending_amount = self._source_amount
        source_initial_value = market.get_value(self._source_amount, self._source).amount
        closed_initial_value = 0.0

        # get required amount from source buckets
        for source_bucket in positions[self._source]:
            amount = source_bucket["amount"]
            diff = min(amount, pending_amount)
            if diff <= DUST_LEVEL:
                continue

            # calculate proportional value according to the amount subtracted
            partial_initial_value = max(0.0, diff / amount) * source_bucket["initial_value"]
            source_bucket["amount"] -= diff
            source_bucket["initial_value"] -= partial_initial_value
            closed_initial_value += partial_initial_value
            pending_amount -= diff
            if pending_amount <= 0:
                break

        if pending_amount > DUST_LEVEL:
            raise PortfolioUpdateException(f"Missing {pending_amount} {self._source}.")

        if self._target not in positions:
            # ensure the target position exists
            positions[self._target] = []

        # add amount to target bucket
        target_buckets = positions[self._target]
        target_buckets.append({"amount": target_amount, "initial_value": source_initial_value})

        self._postprocess_buckets(positions, market)

        return {
            "source_currency": self._source,
            "source_amount": self._source_amount,
            "min_target_amount": self._min_target_amount,
            "target_currency": self._target,
            "target_amount": target_amount,
            "source_initial_value": source_initial_value,
            "closed_initial_value": closed_initial_value
        }

    def __repr__(self):
        return f"Transfer {self._source_amount} {self._source} --> {self._min_target_amount} {self._target}"

    def _postprocess_buckets(self, positions, market):
        for currency, position in positions.items():
            for i, bucket in reversed(list(enumerate(position))):
                if currency == market.target_currency:
                    # reset initial value of target currency
                    bucket["initial_value"] = bucket["amount"]

                if bucket["amount"] < DUST_LEVEL:
                    bucket["amount"] = 0  # discard the dust

                if bucket["initial_value"] < DUST_LEVEL:
                    bucket["initial_value"] = 0

                if bucket["amount"] <= 0:
                    if i > 0:
                        del position[i]  # delete empty buckets, but keep at least one bucket per position
                    else:
                        bucket["initial_value"] = 0  # keep initial value sane

            position.sort(key=operator.itemgetter("initial_value"), reverse=False)
            for i, bucket in reversed(list(enumerate(position))):
                if i == 0:
                    # nothing to merge
                    continue

                if bucket["initial_value"] < MIN_POSITION_BUCKET_VALUE or currency == market.target_currency:
                    position[i - 1]["initial_value"] += bucket["initial_value"]
                    position[i - 1]["amount"] += bucket["amount"]
                    del position[i]
