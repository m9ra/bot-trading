import datetime
import sys

from flask import Flask, render_template, request, make_response
from flask_bootstrap import Bootstrap

from bot_trading import configuration
from bot_trading.configuration import TRADING_ENDPOINT
from bot_trading.core.data.storage_reader import StorageReader
from bot_trading.core.networking.trading_server import TradingServer
from bot_trading.core.web.score_record import ScoreRecord

EXCHANGE_NAME = sys.argv[1]

supported_pairs = ["XRP/EUR", "XMR/EUR", "ETH/EUR", "REP/EUR"]
readers = []
for pair in supported_pairs:
    readers.append(StorageReader(pair))

trading_server = TradingServer(EXCHANGE_NAME, readers)
trading_server.run_server(int(TRADING_ENDPOINT.split(":")[-1]))

web_server = Flask(__name__, template_folder="web/templates", static_folder="web/static")
web_server.secret_key = b'fer234\n\xec]/'
Bootstrap(web_server)


@web_server.route("/profile/<username>")
def profile(username):
    portfolio_state = trading_server.get_portfolio_state(username)
    return render_template("profile.html", username=username, portfolio_state=portfolio_state)


@web_server.route("/history")
def history():
    return render_template("history.html")


@web_server.route("/results_table")
def results_table():
    scores = ScoreRecord.load_for(trading_server)
    return render_template("results_table.html", scores=scores)


@web_server.route("/")
def dashboard():
    endpoint = configuration.TRADING_ENDPOINT
    return render_template("index.html", exchange_name=EXCHANGE_NAME, endpoint=endpoint,
                           supported_pairs=supported_pairs)


@web_server.template_filter('ctime')
def timectime(s):
    if not s:
        return None

    return datetime.datetime.fromtimestamp(s).strftime("%Y-%m-%d %H:%M:%S")


import logging

log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

web_server.run(debug=True, use_reloader=False, host='0.0.0.0', port=8698)
