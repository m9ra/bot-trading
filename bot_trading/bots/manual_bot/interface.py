from copy import deepcopy
from threading import Thread

from flask import jsonify, request, flash

from bot_trading.bots.bot_base import BotBase
from bot_trading.core.data.parsing import parse_pair
from bot_trading.core.messages import log_command
from bot_trading.core.runtime.execution import get_username
from bot_trading.trading.fund import Fund
from bot_trading.trading.portfolio_controller import PortfolioController


class ManualBot(BotBase):
    def __init__(self, web_port, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.update_interval = 0.5
        self.web_port = web_port

        self.interface_state = None
        self._is_web_started = False
        self._last_portfolio = None

    def update_portfolio(self, portfolio: PortfolioController):
        if not self._is_web_started:
            self._is_web_started = True
            self._start_server(portfolio.target_currency, portfolio.currencies, portfolio.pairs)

        self._last_portfolio = portfolio

        present = portfolio.present

        state = {}
        state["timestamp"] = present.timestamp
        state["total_value"] = portfolio.total_value.amount

        state["funds"] = funds = {}
        for currency in portfolio.currencies:
            funds[currency] = {"amount": 0.0, "initial_value": 0.0, "current_value": 0.0}

        for currency, position in portfolio._current_portfolio_state["positions"].items():
            amount = 0.0
            initial_value = 0.0
            for bucket in position:
                amount += bucket["amount"]
                initial_value += bucket["initial_value"]

            current_value = present.get_value(Fund(amount, currency)).amount
            funds[currency].update({
                "amount": amount,
                "initial_value": initial_value,
                "current_value": current_value
            })

        state["prices"] = prices = {}
        for pair in portfolio.pairs:
            orderbook = present.get_pricebook(*parse_pair(pair))
            prices[pair] = {
                "b": orderbook.buy_levels[0][0],
                "s": orderbook.sell_levels[-1][0]
            }

        self.interface_state = state

    def _start_server(self, target_currency, supported_currencies, direct_pairs):
        from flask import Flask, render_template
        from flask_bootstrap import Bootstrap

        server = Flask(__name__)
        server.secret_key = b'fesdfsfr234\n\xec]/'
        Bootstrap(server)

        supported_currencies = sorted(supported_currencies)
        supported_currencies.remove(target_currency)
        supported_currencies.insert(0, target_currency)

        direct_pairs = sorted(direct_pairs)
        direct_pairs = [parse_pair(pair) for pair in direct_pairs]

        @server.route("/request_transfer", methods=["POST"])
        def _request_transfer():
            source_currency = request.json.get("source_currency")
            source_amount = request.json.get("source_amount")
            target_currency = request.json.get("target_currency")

            message = self._web_request_transfer(source_amount, source_currency, target_currency)
            return jsonify({"message": message})

        @server.route("/", methods=["GET", "POST"])
        def _interface_index():
            return render_template("index.html",
                                   supported_currencies=supported_currencies,
                                   direct_pairs=direct_pairs,
                                   username=get_username()
                                   )

        @server.route("/interface_state")
        def _interface_state():
            state = self.interface_state
            if state is None:
                return "null"

            return jsonify(state)

        import logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)

        Thread(target=lambda: server.run(debug=True, use_reloader=False, host='0.0.0.0', port=self.web_port),
               daemon=True).start()

    def _web_request_transfer(self, source_amount, source_currency, target_currency):
        portfolio: PortfolioController = self._last_portfolio
        state = portfolio._current_portfolio_state
        try:
            if source_amount.strip().lower() == "all":
                source_amount = portfolio.get_fund_with(source_currency, gain_greater_than=0).amount
            else:
                source_amount = float(source_amount)

            commands = portfolio.create_transfer_commands(Fund(source_amount, source_currency), target_currency)
            if not commands:
                return f"Transfer path is not available between {source_currency} to {target_currency}"

            state = deepcopy(state)
            for command in commands:
                command.apply(state, portfolio._market)

        except Exception as e:
            return str(e)

        is_success = True
        for command in commands:
            log_command(command)
            is_success = is_success and self.portfolio_connector.execute(command)

        if is_success:
            return f"Successful transfer: {commands}"
        else:
            return f"Transfer declined: {commands}"
