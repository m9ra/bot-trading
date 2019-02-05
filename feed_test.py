import json

from websocket import create_connection

from configuration import TRACKED_PAIRS, WS_URL
from data.storage import Storage

ws = create_connection(WS_URL)


def send(data):
    json_data = json.dumps(data)
    print(f">> {json_data}")
    ws.send(json_data)


def receive():
    data = ws.recv()
    print(f"<< {data}")
    return data


receive()
send({
    "event": "subscribe",
    "pair": TRACKED_PAIRS,
    "subscription": {
        "name": "book"
    }
})

pair_to_storage = {}
channel_to_pair = {}

for pair in TRACKED_PAIRS:
    pair_to_storage[pair] = Storage(pair)


def parse_event(data_obj: dict):
    event = data_obj.get("event", None)
    if event == "subscriptionStatus":
        channel_id = data_obj["channelID"]
        pair = data_obj["pair"]
        channel_to_pair[channel_id] = pair

        if data_obj["status"] != "subscribed":
            raise AssertionError("Invalid subscription status")


def parse_payload(data_obj):
    channel_id = data_obj[0]
    payloads=data_obj[1:]
    pair = channel_to_pair[channel_id]
    storage = pair_to_storage[pair]
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


while True:
    data = receive()
    data_obj = json.loads(data)

    if isinstance(data_obj, dict):
        parse_event(data_obj)

    elif isinstance(data_obj, list):
        parse_payload(data_obj)
