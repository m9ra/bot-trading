import _thread
import base64
import time
from threading import Thread, RLock, Event
from typing import List, Dict, Any

import jsonpickle

from bot_trading.configuration import LOCAL_DISK_CACHE_SIZE
from bot_trading.core.data.disk_cache import DiskCache
from bot_trading.core.data.storage_writer import StorageWriter
from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.core.messages import log_cache
from bot_trading.core.networking.remote_entry_reader import RemoteEntryReader
from bot_trading.core.networking.socket_client import SocketClient


class RemoteObserver(object):
    def __init__(self, remote_endpoint: str, username: str, password: str):
        self._remote_endpoint = remote_endpoint
        self._username = username
        self._password = password

        self._pairs: List[str] = None
        self._readers: Dict[str, RemoteEntryReader] = None

        self._client: SocketClient = None
        self._disk_cache: DiskCache = None
        if LOCAL_DISK_CACHE_SIZE > 0:
            self._disk_cache = DiskCache(LOCAL_DISK_CACHE_SIZE)

        self._L_commands = RLock()
        self._current_command_id = 0
        self._command_events: Dict[int, Event] = {}
        self._command_results: Dict[int, Any] = {}
        self.shutdown = False

    def get_reader(self, pair):
        return self._readers.get(pair)

    def connect(self, mode):
        self._raw_connect(mode)

        Thread(target=self._client_reader, args=[], daemon=True).start()

    def _raw_connect(self, mode):
        self._client = self._create_client(mode)
        welcome_message = self._client.read_json()
        pairs_info = welcome_message["pairs_info"]
        self._pairs = list(pairs_info.keys())
        readers = {}
        for pair, info in pairs_info.items():
            readers[pair] = RemoteEntryReader(pair, info["entry_count"], self)
        self._readers = readers

    def get_readers(self):
        print("Storage synchronization...")
        while self._readers is None:
            time.sleep(0.1)  # wait until storages are synchronized

        print("\t complete")

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
        # bucket_entries = self._decode_chunk(pair, response["bucket"])
        # self._readers[pair]._receive_bucket(index, bucket_entries)

        return index * StorageWriter.bucket_entry_count

    def async_get_bucket(self, pair, bucket_index):
        if self._disk_cache:
            bucket_bytes = self._disk_cache.get_bucket(pair, bucket_index)
            if bucket_bytes:
                entries = TradeEntry.from_chunk(pair, bucket_bytes)
                self._readers[pair]._receive_bucket(bucket_index, entries)
                return

        log_cache(f"Requesting remote bucket {pair} {bucket_index}")
        self._client.send_json({
            "name": "async_get_bucket",
            "pair": pair,
            "bucket_index": bucket_index,
        })

    def send_portfolio_command_request(self, command):
        return self._send_command({
            "name": "update_portfolio_state",
            "update_command": jsonpickle.dumps(command)
        })

    def receive_portfolio_state(self):
        return self._send_command({
            "name": "receive_portfolio_state",
        })["portfolio_state"]

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
                self._readers[pair]._receive_peek_entries(start_entry_index, entries)
            elif "bucket" in message:
                pair = message["pair"]
                bucket_index = message["bucket_index"]
                base64_chunk = message["bucket"]
                if self._disk_cache:
                    payload = base64.b64decode(base64_chunk)
                    self._disk_cache.set_bucket(pair, bucket_index, payload)

                self._readers[pair]._receive_bucket(bucket_index, self._decode_chunk(pair, base64_chunk))

            elif "id" in message:
                # response for a command came
                id = message["id"]
                self._command_results[id] = message
                self._command_events[id].set()
            elif "system" in message:
                system_command = message["system"]
                if system_command == "shutdown":
                    print("\nSHUTDOWN COMMAND RECEIVED")
                    self.shutdown = True
                    self._client.disconnect()
                    break
                else:
                    raise AssertionError(f"Unknown system command {message}")

            else:
                raise AssertionError(f"Unknown message {message}")

        print()
        print("OBSERVER DISCONNECTED")
        print("Starting cleanups")
        print("\t release commands")
        for event in self._command_events.values():
            # release all commands
            event.set()

        print("\t release readers")
        for reader in self._readers.values():
            reader.close()

        print("\t interrupt main")
        _thread.interrupt_main()

    def _create_client(self, access_mode):
        client = SocketClient()
        host, port = self._remote_endpoint.split(":")
        client.connect(host, int(port))
        client.send_json({
            "username": self._username,
            "password": self._password,
            "access_mode": access_mode
        })
        return client

    def _decode_chunk(self, pair, base64_chunk):
        chunk = base64.b64decode(base64_chunk)
        entries = TradeEntry.from_chunk(pair, chunk)
        return entries
