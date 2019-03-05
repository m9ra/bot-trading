from collections import defaultdict

from bots.bot_base import BotBase


class IntervalPredictionBot(BotBase):
    prediction_interval_length = 10.0  # how long interval the bot uses for price estimation

    def update_portfolio(self, portfolio):
        """
        The bot will transfer all profitable equities to more promising currencies (proportionally).
        In case all currencies are falling, it implicitly causes transfer to the target currency.
        NOTE:
            profitable means that the current target value is >= than the initial value (including fees)
        """

        predicted_currency_gains = self._predict_currency_gains(portfolio)
        if not predicted_currency_gains:
            # there is nothing to do when predictions are available
            return

        source, amount, target = self._get_largest_improvement(predicted_currency_gains, portfolio)

        if amount:
            portfolio.request_conversion(source, amount, target)

    def _predict_currency_gains(self, portfolio):
        """
        Predicts expected gains for all currencies.
        It does NOT take fees into consideration.
        """
        gains = defaultdict(lambda: 1.0)

        for currency in portfolio.currencies:
            history = portfolio.get_history(currency)
            # if we knew amount to be traded, we could get estimation with fees
            current_value = history.get_value(0)
            past_interval_value = history.get_value(IntervalPredictionBot.prediction_interval_length)
            if current_value is None or past_interval_value is None:
                return None

            past_growth = current_value - past_interval_value
            next_price = current_value + past_growth  # assume that the value will grow same as in the past
            gains[currency] = next_price / current_value

        return gains

    def _get_largest_improvement(self, predicted_currency_gains, portfolio):
        """
        Tries to balance the whole portfolio proportionally to currencies with predicted gains >= 1.0
        Returns the biggest difference to the disproportion.
        """

        sorted_diffs = self._get_target_diffs_sorted(predicted_currency_gains, portfolio)
        if not sorted_diffs:
            # there are no diffs to improve
            return None, 0, None

        # find how much of currency is available for improvements
        best_available_currency = None
        best_available_amount = 0.0
        for currency, amount_diff in sorted_diffs:
            # first, find largest available amount (positive amounts are on the list begining)
            available_amount = min(amount_diff, portfolio.get_balance(currency))
            if available_amount > best_available_amount:
                best_available_amount = available_amount
                best_available_currency = currency

        target_currency, target_diff = sorted_diffs[-1]
        has_available_amount = best_available_currency is not None
        has_available_target = target_diff < 0  # there is some missing amount
        if has_available_amount and has_available_target:
            # improve by passing largest amount to most needed currency
            return best_available_currency, min(best_available_amount, -target_diff), target_currency

        return None, 0, None  # no improvement was found

    def _get_target_diffs_sorted(self, predicted_currency_gains, portfolio):
        positive_gain_sum = sum(gain for gain in predicted_currency_gains.values() if gain >= 1)
        if positive_gain_sum <= 0:
            # there are no loss-less options, so rather stay still
            # NOTE: the target currency should be always 1, so this should not happen
            return []

        # calculate diffs to the desired, proportional amounts
        diffs = []
        for currency, gain in predicted_currency_gains.items():
            if gain >= 1:
                # promising currencies will split value proportionally
                target_ratio = gain / positive_gain_sum
                target_value = target_ratio * portfolio.total_value
            else:
                # non promising currencies should be of zero value
                target_value = 0

            target_amount = portfolio.get_amount_of_value(target_value, currency)
            current_amount = portfolio.get_balance(currency)
            diffs.append((currency, current_amount - target_amount))

        return sorted(diffs, key=lambda diff: diff[1], reverse=True)
