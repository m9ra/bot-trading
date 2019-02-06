import json
import logging
from time import sleep

from data.storage import Storage

from websocket import create_connection


class FeedWriter(object):
    def __init__(self, ws_url, pairs):
        self._ws_url = ws_url
        self._pairs = pairs

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
            except:
                logging.exception("_run raised an exception")

            sleep(1)

    def _run(self):
        logging.info("_run starts")

        self._ws = create_connection(self._ws_url)

        self.receive()
        self.send({
            "event": "subscribe",
            "pair": self._pairs,
            "subscription": {
                "name": "book"
            }
        })

        self.pair_to_storage = {}
        self.channel_to_pair = {}

        for pair in self._pairs:
            self.pair_to_storage[pair] = Storage(pair)

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

    def send(self, data):
        json_data = json.dumps(data)
        print(f">> {json_data}")
        self._ws.send(json_data)

    def receive(self):
        data = self._ws.recv()
        print(f"<< {data}")
        return data

    def parse_event(self, data_obj: dict):
        event = data_obj.get("event", None)
        if event == "subscriptionStatus":
            channel_id = data_obj["channelID"]
            pair = data_obj["pair"]
            self.channel_to_pair[channel_id] = pair

            if data_obj["status"] != "subscribed":
                raise AssertionError("Invalid subscription status")

    def parse_payload(self, data_obj):
        channel_id = data_obj[0]
        payloads = data_obj[1:]
        pair = self.channel_to_pair[channel_id]
        storage = self.pair_to_storage[pair]
        for payload in payloads:
            for key, value in payload.items():
                if key not in ["as", "bs", "a", "b"]:
                    raise AssertionError("Unknown key " + key)

                snapshot = len(key) == 2
                is_buy = key[0] == "b"

                if snapshot:
                    storage.reset(is_buy)

                for price_s, amount_s, timestamp_s in value:
                    storage.write(is_buy, float(price_s), float(amount_s), float(timestamp_s))
