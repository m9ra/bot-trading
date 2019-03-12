import base64
import time
from threading import Thread, RLock, Event
from typing import List, Dict, Any

from data.storage_writer import StorageWriter
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
        self._L_commands = RLock()
        self._current_command_id = 0
        self._command_events: Dict[int, Event] = {}
        self._command_results: Dict[int, Any] = {}

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

    def get_readers(self):
        print("Waiting for storage synchronization")
        while self._readers is None:
            time.sleep(0.1)  # wait until storages are synchronized

        print("Synchronized")

        return self._readers.values()

    def get_pairs(self):
        return self._pairs

    def find_pricebook_start(self, pair, start_time: float):
        response = self._send_command({
            "name": "find_pricebook_start",
            "pair": pair,
            "start": start_time
        })

        index = int(response["bucket_index"])
        #bucket_entries = self._decode_chunk(pair, response["bucket"])
        #self._readers[pair]._receive_bucket(index, bucket_entries)

        return index * StorageWriter.bucket_entry_count

    def get_bucket(self, pair, bucket_index):
        response = self._send_command({
            "name": "get_bucket",
            "pair": pair,
            "bucket_index": bucket_index,
        })

        return self._decode_chunk(pair, response["bucket"])

    def _send_command(self, command):
        with self._L_commands:
            id = self._current_command_id
            self._current_command_id += 1

        event = Event()
        self._command_events[id] = event

        command["id"] = id
        self._client.send_json(command)

        event.wait()  # wait until response comes from server
        del self._command_events[id]
        result = self._command_results.pop(id)
        return result

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

                entries = self._decode_chunk(pair, base64_chunk)
                self._readers[pair]._receive_entries(start_entry_index, entries)
            elif "id" in message:
                # response for a command came
                print(message)
                id = message["id"]
                self._command_results[id] = message
                self._command_events[id].set()

            else:
                raise AssertionError(f"Unknown message {message}")

        print("Observer disconnected")

    def _create_client(self):
        client = SocketClient()
        host, port = self._remote_endpoint.split(":")
        client.connect(host, int(port))
        client.send_json({
            "username": self._username,
            "password": self._password,
        })
        return client

    def _decode_chunk(self, pair, base64_chunk):
        chunk = base64.b64decode(base64_chunk)
        entries = TradeEntry.from_chunk(pair, chunk)
        return entries
