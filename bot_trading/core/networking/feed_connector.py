import json
import logging
import time
from time import sleep
from typing import Callable, List

from websocket import create_connection, WebSocketConnectionClosedException, WebSocketBadStatusException

from bot_trading.core.configuration import BOOK_DEPTH
from bot_trading.core.processors.processor_base import ProcessorBase


class FeedWriter(object):
    def __init__(self, feed_ws_url: str, pairs: List[str], processor_factory: Callable[[str], ProcessorBase]):
        self._feed_ws_url = feed_ws_url
        self._pairs = pairs
        self._processor_factory = processor_factory
        self._pair_to_processor = None

        # configure logging
        formatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
        root_logger = logging.getLogger()

        file_handler = logging.FileHandler("/tmp/price_satellite.log")
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        root_logger.setLevel(logging.DEBUG)

        self._logger = root_logger
        self._logger.info("LOGGER INITIALIZED")

    def run(self):
        while True:
            try:
                self._run()
            except StopIteration:
                logging.info("StopIteration")
            except WebSocketConnectionClosedException:
                logging.warning("Connection closed exception")
            except WebSocketBadStatusException:
                logging.warning("Websocket bad status exception")
            except:
                logging.exception("_run raised an exception")

            sleep(1)

    def _run(self):
        logging.info("_run starts")

        self._channel_to_pair = {}
        self._pair_to_processor = {}
        self._initialize_processors()

        self._ws = create_connection(self._feed_ws_url)

        self.receive()
        self.send({
            "event": "subscribe",
            "pair": self._pairs,
            "subscription": {
                "name": "book",
                "depth": BOOK_DEPTH
            }
        })

        parsed_events = 0
        while True:
            data = self.receive()
            data_obj = json.loads(data)

            if isinstance(data_obj, dict):
                self.parse_event(data_obj)

            elif isinstance(data_obj, list):
                self.parse_payload(data_obj)

            parsed_events += 1
            if parsed_events % 1e5 == 0:
                logging.info(f"\t events collected: {parsed_events}")

    def _initialize_processors(self):
        for pair in self._pairs:
            processor = self._processor_factory(pair)
            self._pair_to_processor[pair] = processor

    def send(self, data):
        json_data = json.dumps(data)
        self._logger.info(f">> {json_data}")
        self._ws.send(json_data)

    def receive(self):
        data = self._ws.recv()
        # self._logger.info(f"<< {data}")
        return data

    def parse_event(self, data_obj: dict):
        event = data_obj.get("event", None)
        if event == "subscriptionStatus":
            channel_id = data_obj["channelID"]
            pair = data_obj["pair"]
            self._channel_to_pair[channel_id] = pair

            if data_obj["status"] != "subscribed":
                raise AssertionError("Invalid subscription status")

    def parse_payload(self, data_obj):
        print(data_obj)
        channel_id = data_obj[0]
        channel_name, pair_name = data_obj[-2:]
        payloads = data_obj[1:-2]

        pair = self._channel_to_pair[channel_id]
        processor = self._pair_to_processor[pair]
        processor.log_network_data(data_obj)

        for payload in payloads:
            for key, values in payload.items():
                if key not in ["as", "bs", "a", "b"]:
                    raise AssertionError("Unknown key " + key)

                for value in values:
                    snapshot = len(key) == 2
                    is_buy = key[0] == "b"

                    if snapshot:
                        processor.reset(is_buy)

                    if len(value) == 4:
                        republish_field = value[-1]
                        value = value[:3]

                    price_s, amount_s, timestamp_s = value
                    processor.write(is_buy, float(price_s), float(amount_s), float(timestamp_s))

        processor.flush()
