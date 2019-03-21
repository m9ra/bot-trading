import os

WS_URL_SANDBOX = "wss://ws-sandbox.kraken.com"
WS_URL = "wss://ws.kraken.com"

BOOK_DEPTH = 10
TRACKED_PAIRS = ["ADA/CAD", "ADA/ETH", "ADA/EUR", "ADA/USD", "ADA/XBT", "BCH/EUR", "BCH/USD", "BCH/XBT", "BSV/EUR",
                 "BSV/USD", "BSV/XBT", "DASH/EUR", "DASH/USD", "DASH/XBT", "EOS/ETH", "EOS/EUR", "EOS/USD", "EOS/XBT",
                 "GNO/ETH", "GNO/EUR", "GNO/USD", "GNO/XBT", "QTUM/CAD", "QTUM/ETH", "QTUM/EUR", "QTUM/USD",
                 "QTUM/XBT",
                 "USDT/USD", "ETC/ETH", "ETC/XBT", "ETC/EUR", "ETC/USD", "ETH/XBT", "ETH/CAD", "ETH/EUR", "ETH/GBP",
                 "ETH/JPY", "ETH/USD", "LTC/XBT", "LTC/EUR", "LTC/USD", "MLN/ETH", "MLN/XBT", "REP/ETH", "REP/XBT",
                 "REP/EUR", "REP/USD", "STR/EUR", "STR/USD", "XBT/CAD", "XBT/EUR", "XBT/GBP", "XBT/JPY", "XBT/USD",
                 "BTC/CAD", "BTC/EUR", "BTC/GBP", "BTC/JPY", "BTC/USD", "XDG/XBT", "XLM/XBT", "DOGE/XBT", "STR/XBT",
                 "XLM/EUR", "XLM/USD", "XMR/XBT", "XMR/EUR", "XMR/USD", "XRP/XBT", "XRP/CAD", "XRP/EUR", "XRP/JPY",
                 "XRP/USD", "ZEC/XBT", "ZEC/EUR", "ZEC/JPY", "ZEC/USD", "XTZ/CAD", "XTZ/ETH", "XTZ/EUR", "XTZ/USD",
                 "XTZ/XBT"]

DUST_LEVEL = 1e-20  # amounts below this will be considered dust and converted to zero
MIN_POSITION_BUCKET_VALUE = 1.0  # if the position bucket value is lower, it will get merged to other bucket

TRADING_ENDPOINT = os.getenv("ENDPOINT", "packa2.cz:8697")
INITIAL_AMOUNT = 1000.0
TARGET_CURRENCY = "EUR"

# defines which logging messeges will show up
# values NETWORK, CACHE, EXECUTOR, COMMAND, PORTFOLIO
LOG_LEVELS = {
    # "NETWORK",
    "CACHE",
    "EXECUTOR",
    "COMMAND",
    "PORTFOLIO"
}
