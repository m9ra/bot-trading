import datetime
import json
import os
import sys
from collections import defaultdict

from flask import Flask, render_template, request
from flask_bootstrap import Bootstrap

from bot_trading.core.configuration import TARGET_CURRENCY, SERVER_SUPPORTED_PAIRS
from bot_trading.core.data.parsing import make_pair

os.environ["BOT_USERNAME"] = "system@email.cz"

from bot_trading.configuration import TRADING_ENDPOINT
from bot_trading.core.data.storage_reader import StorageReader
from bot_trading.core.networking.trading_server import TradingServer
from bot_trading.core.web.history_cache import HistoryCache
from bot_trading.core.web.score_record import ScoreRecord

EXCHANGE_NAME = sys.argv[1]


history_cache = {}
readers = []
print("Preparing readers")
for pair in SERVER_SUPPORTED_PAIRS:
    print(f"\t {pair}")
    storage = StorageReader(pair)
    readers.append(storage)
    history_cache[pair] = HistoryCache(storage, 10.0, 5 * 3600)
    history_cache[pair].get_data()

print("readers are ready")

trading_server = TradingServer(EXCHANGE_NAME, readers)
trading_server.run_server(int(TRADING_ENDPOINT.split(":")[-1]))

web_server = Flask(__name__, template_folder="web/templates", static_folder="web/static")
web_server.secret_key = b'fer234\n\xec]/'
Bootstrap(web_server)


@web_server.route("/profile/<username>")
def profile(username):
    return render_template("profile.html", username=username)


@web_server.route("/history")
def history():
    return render_template("history.html")


@web_server.route("/portfolio_values")
def portfolio_values():
    return render_template("portfolio_values.html")


@web_server.route("/graphs")
def graphs():
    return render_template("graphs.html", supported_pairs=SERVER_SUPPORTED_PAIRS)


@web_server.route("/live_graph/<c1>/<c2>")
def live_graph(c1, c2):
    return render_template("live_graph.html", pair=make_pair(c1, c2))


@web_server.route("/portfolio")
def portfolio():
    username = request.args.get("username")
    portfolio_state, portfolio_value = trading_server.get_portfolio_state(username)

    funds = {}
    for currency, position in portfolio_state["positions"].items():
        amount = 0.0
        initial_value = 0.0
        for bucket in position:
            amount += bucket["amount"]
            initial_value += bucket["initial_value"]

        current_value = trading_server._market.get_value(amount, currency).amount
        funds[currency] = {
            "amount": amount,
            "initial_value": initial_value,
            "current_value": current_value
        }
    return render_template("portfolio.html", funds=funds, portfolio_value=portfolio_value)


@web_server.route("/history_table")
def history_table():
    username = request.args.get("username")
    history, transfer_count = trading_server.load_transfer_history(username)
    return render_template("history_table.html", history=history, transfer_count=transfer_count, username=username)


@web_server.route("/results_table")
def results_table():
    scores = ScoreRecord.load_for(trading_server)
    return render_template("results_table.html", scores=scores)


@web_server.route("/bid_asks")
def pricebook_table():
    bid_asks = trading_server.get_bid_asks()
    return render_template("bid_asks.html", bid_asks=bid_asks)


@web_server.route("/")
def index():
    endpoint = TRADING_ENDPOINT
    return render_template("index.html", exchange_name=EXCHANGE_NAME, endpoint=endpoint,
                           supported_pairs=SERVER_SUPPORTED_PAIRS)


@web_server.route("/portfolio_values_data")
def portfolio_values_data():
    result = defaultdict(list)
    for value in trading_server.load_portfolio_values():
        for user, pv in value["portfolio_values"]:
            result[user].append((value["timestamp"], pv))

    return json.dumps(result)


@web_server.route("/pair_data/<pair>")
def pair_data(pair):
    pair = pair.replace("-", "/")
    cache = history_cache[pair]

    transfers_raw, _ = trading_server.load_transfer_history()
    markers = []
    for transfer in transfers_raw:
        source = transfer["update_result"].get("source_currency")
        target = transfer["update_result"].get("target_currency")

        if not source or not target or (make_pair(source, target) != pair and make_pair(target, source) != pair):
            continue

        if source == TARGET_CURRENCY:
            is_buy = 1
        else:
            is_buy = 0

        markers.append({
            "u": transfer["username"],
            "b": is_buy,
            "t": transfer["market_timestamp"]
        })

    result = {
        "pair": pair,
        "data": cache.get_data(),
        "markers": markers
    }
    return json.dumps(result)


@web_server.template_filter('ctime')
def timectime(s):
    if not s:
        return None

    return datetime.datetime.fromtimestamp(s).strftime("%Y-%m-%d %H:%M:%S")


@web_server.template_filter('as_target')
def as_target(v):
    if v < 10.0:
        return "%.4f €" % v
    else:
        return "%.2f €" % v


@web_server.template_filter('as_amount')
def as_amount(v):
    return "%.5f" % v


import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

web_server.run(debug=True, use_reloader=False, host='0.0.0.0', port=8698)
