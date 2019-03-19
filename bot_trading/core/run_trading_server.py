import datetime
import json
import sys

from flask import Flask, render_template
from flask_bootstrap import Bootstrap

from bot_trading import configuration
from bot_trading.configuration import TRADING_ENDPOINT
from bot_trading.core.data.storage_reader import StorageReader
from bot_trading.core.networking.trading_server import TradingServer
from bot_trading.core.web.history_cache import HistoryCache
from bot_trading.core.web.score_record import ScoreRecord

EXCHANGE_NAME = sys.argv[1]

supported_pairs = ["XRP/EUR", "XMR/EUR", "ETH/EUR", "REP/EUR"]
history_cache = {}
readers = []
print("Preparing readers")
for pair in supported_pairs:
    print(f"\t {pair}")
    storage = StorageReader(pair)
    readers.append(storage)
    history_cache[pair] = HistoryCache(storage, 5000, 3600)
    history_cache[pair].get_data()

print("readers are ready")

trading_server = TradingServer(EXCHANGE_NAME, readers)
trading_server.run_server(int(TRADING_ENDPOINT.split(":")[-1]))

web_server = Flask(__name__, template_folder="web/templates", static_folder="web/static")
web_server.secret_key = b'fer234\n\xec]/'
Bootstrap(web_server)


@web_server.route("/profile/<username>")
def profile(username):
    portfolio_state = trading_server.get_portfolio_state(username)
    history = trading_server.load_transfer_history(username)
    return render_template("profile.html", username=username, portfolio_state=portfolio_state, history=history)


@web_server.route("/history")
def history():
    history = trading_server.load_transfer_history()
    return render_template("history.html", history=history)


@web_server.route("/results_table")
def results_table():
    scores = ScoreRecord.load_for(trading_server)
    return render_template("results_table.html", scores=scores)


@web_server.route("/")
def index():
    endpoint = configuration.TRADING_ENDPOINT
    return render_template("index.html", exchange_name=EXCHANGE_NAME, endpoint=endpoint,
                           supported_pairs=supported_pairs)


@web_server.route("/pair_data/<pair>")
def pair_data(pair):
    pair = pair.replace("-", "/")
    cache = history_cache[pair]

    result = {
        "pair": pair,
        "data": cache.get_data()
    }
    return json.dumps(result)


@web_server.template_filter('ctime')
def timectime(s):
    if not s:
        return None

    return datetime.datetime.fromtimestamp(s).strftime("%Y-%m-%d %H:%M:%S")


import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

web_server.run(debug=False, use_reloader=False, host='0.0.0.0', port=8698)
