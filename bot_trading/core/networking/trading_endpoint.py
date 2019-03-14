import base64
import socket
import traceback
from threading import Thread, RLock
from typing import List, Dict

from bot_trading.core.data.storage_reader import StorageReader
from bot_trading.core.data.storage_writer import StorageWriter
from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.core.networking.socket_client import SocketClient


class TradingEndpoint(object):
    def __init__(self, storages: List[StorageReader]):
        self._logged_clients: Dict[str, SocketClient] = {}
        self._L_clients = RLock()
        self._storages = {}

        for storage in storages:
            self._storages[storage.pair] = storage
            storage.subscribe(self._feed_handler)

    def start_accepting(self, port):
        Thread(target=self._accept_clients, args=[port], daemon=True).start()

    def _login(self, client: SocketClient):
        # receive login information
        login_message = client.read_json()
        if not login_message:
            return None

        username = login_message["username"]

        with self._L_clients:
            client.username = username
            self._logout(username)  # logout possible previous client
            self._logged_clients[username] = client
            print(f"Login: {username}")

        return username

    def _logout(self, username: str):
        with self._L_clients:
            client = self._logged_clients.pop(username, None)
            if client:
                print(f"Logout: {username}")
                client.disconnect()

    def _feed_handler(self, first_entry_index: int, entries: List[TradeEntry]):
        if not self._logged_clients:
            return  # no clients == nothing to do

        pair = entries[0].pair

        chunk = []
        for entry in entries:
            if entry.pair != pair:
                raise AssertionError(f"Expected {pair} but got {entry.pair}")

            chunk.extend(TradeEntry.to_chunk(entry))

        base64_chunk = self._encode_chunk(chunk)
        clients = list(self._logged_clients.values())
        for client in clients:
            self._send_entries_chunk(client, pair, first_entry_index, base64_chunk)

    def _send_entries_chunk(self, socket_client: SocketClient, pair: str, first_entry_index: int, base64_chunk):
        try:
            socket_client.send_json({
                "f": pair,
                "i": first_entry_index,
                "c": base64_chunk
            })
        except:
            print(f"Client feed failed: {socket_client.username}")

    def _handle_client(self, socket, addr):
        client = SocketClient(socket)
        username = None
        try:
            username = self._login(client)
            if not username:
                return

            pairs_info = {}
            for pair, storage in self._storages.items():
                pairs_info[pair] = {
                    "entry_count": storage.get_entry_count()
                }

            client.send_json({
                "pairs_info": pairs_info
            })

            while client.is_connected:
                command = client.read_json()
                if command is None:
                    break  # client disconnected

                c = command.get("name", None)
                response = {"id": command.get("id", None)}

                if c == "async_get_bucket":
                    pair = command["pair"]
                    bucket_index = int(command["bucket_index"])

                    storage = self._storages[pair]
                    chunk = storage.get_bucket_chunk(bucket_index)
                    response["pair"] = pair
                    response["bucket_index"] = bucket_index
                    response["bucket"] = self._encode_chunk(chunk)

                elif c == "find_pricebook_start":
                    pair = command["pair"]
                    start = float(command["start"])

                    storage = self._storages[pair]
                    start_index = storage.find_pricebook_start(start)
                    bucket_index = int(start_index / StorageWriter.bucket_entry_count)
                    # chunk = storage.get_bucket_chunk(bucket_index)
                    # response["bucket"] = self._encode_chunk(chunk)
                    response["bucket_index"] = bucket_index

                else:
                    raise AssertionError(f"Unknown command received: {command}")

                client.send_json(response)

        except:
            traceback.print_exc()
            print(f"Exception for {addr}")
        finally:

            if username:
                self._logout(username)

            print(f"Client disconnected: {username}")

    def _accept_clients(self, port):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', port))
        s.listen()

        while True:
            print("accepting clients...")
            client_socket, addr = s.accept()
            Thread(target=self._handle_client, args=[client_socket, addr], daemon=True).start()

    def _encode_chunk(self, chunk):
        base64_chunk = base64.b64encode(bytearray(chunk)).decode("ascii")
        return base64_chunk
