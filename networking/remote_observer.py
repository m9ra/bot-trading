import base64
import time
from threading import Thread
from typing import List, Dict

from data.trade_entry import TradeEntry
from networking.remote_entry_reader import RemoteEntryReader
from networking.socket_client import SocketClient


class RemoteObserver(object):
    def __init__(self, remote_endpoint: str, username: str, password: str):
        self._remote_endpoint = remote_endpoint
        self._username = username
        self._password = password

        self._pairs: List[str] = None
        self._readers: Dict[str, RemoteEntryReader] = None

        self._client: SocketClient = None

    def get_reader(self, pair):
        return self._readers.get(pair)

    def connect(self):
        self._client = self._create_client()
        self._pairs = list(self._client.read_json()["pairs"])

        readers = {}
        for pair in self._pairs:
            readers[pair] = RemoteEntryReader(pair, 0, self)

        self._readers = readers

        Thread(target=self._client_reader, args=[], daemon=True).start()

    def _create_client(self):
        client = SocketClient()
        host, port = self._remote_endpoint.split(":")
        client.connect(host, int(port))
        client.send_json({
            "username": self._username,
            "password": self._password,
        })
        return client

    def _client_reader(self):
        while True:
            message = self._client.read_json()
            if message is None:
                break

            if "f" in message:
                # we got feed
                pair = message["f"]
                start_entry_index = message["i"]
                base64_chunk = message["c"]

                chunk = base64.b64decode(base64_chunk)
                entries = TradeEntry.from_chunk(pair, chunk)
                self._readers[pair]._receive_entries(start_entry_index, entries)

            else:
                raise AssertionError(f"Unknown message {message}")

        print("Observer disconnected")

    def get_readers(self):
        print("Waiting for storage synchronization")
        while self._readers is None:
            time.sleep(0.1)  # wait until storages are synchronized

        print("Synchronized")

        return self._readers.values()

    def get_pairs(self):
        return self._pairs
