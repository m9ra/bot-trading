import base64
import socket
import time
import traceback
from copy import deepcopy
from threading import Thread, RLock
from typing import List, Dict

import jsonpickle
from pymongo import MongoClient

from bot_trading.core.configuration import TARGET_CURRENCY, INITIAL_AMOUNT
from bot_trading.core.data.parsing import parse_pair
from bot_trading.core.data.storage_reader import StorageReader
from bot_trading.core.data.storage_writer import StorageWriter
from bot_trading.core.data.trade_entry import TradeEntry
from bot_trading.core.networking.socket_client import SocketClient
from bot_trading.core.processors.pricebook_processor import PricebookProcessor
from bot_trading.core.runtime.execution import get_initial_portfolio_state
from bot_trading.core.runtime.validation import validate_email
from bot_trading.trading.market import Market
from bot_trading.trading.peek_connector import PeekConnector
from bot_trading.trading.portfolio_controller import PortfolioController

_db_name = "bot_trading"
_client = MongoClient()
_db = _client[_db_name]


class TradingServer(object):
    def __init__(self, name, storages: List[StorageReader]):
        self._L_collection = RLock()
        self._L_market = RLock()

        self._collection = _db[name]
        # self._collection.users.drop()
        # self._collection.transfsers.drop()
        # self._collection.portfolio_values.drop()

        self._logged_clients: Dict[str, SocketClient] = {}
        self._L_clients = RLock()
        self._storages = {}
        self._last_time_check = time.time()

        for storage in storages:
            self._storages[storage.pair] = storage
            storage.subscribe(self._feed_handler)

        connector = PeekConnector(list(self._storages.values()))
        self._market = Market(TARGET_CURRENCY, list(self._storages.keys()), connector)

        Thread(target=self._run_market, daemon=True).start()
        print("Market synchronization")
        while not self._market.present.is_available:
            time.sleep(0.1)
        print("\t complete")

    @property
    def currencies(self):
        return list(self._storages.keys())

    def load_portfolio_values(self):
        cursor = self._collection.portfolio_values.find({})
        return cursor.sort("timestamp", -1).limit(1000)

    def load_accounts(self):
        with self._L_collection:
            return list(self._collection.users.find({}))

    def load_transfer_history(self, username=None):
        with self._L_collection:
            if username:
                query = {"username": username}
            else:
                query = {}

            cursor = self._collection.transfers.find(query)
            return list(cursor.sort("real_time", -1).limit(100)), cursor.count()

    def is_user_online(self, username):
        return username in self._logged_clients

    def get_portfolio_state(self, username):
        user_data = self._get_user_data(username)
        if user_data is None:
            return None

        return user_data["portfolio_state"], user_data["portfolio_value"]

    def get_bid_asks(self):
        result = []
        present = self._market.present
        for pair in self._market.direct_currency_pairs:
            sc, tc = parse_pair(pair)
            if tc != self._market.target_currency:
                continue

            pb = present.get_pricebook(sc, tc)
            result.append([sc] + pb.bid_ask)

        return result

    def run_server(self, port):
        Thread(target=self._accept_clients, args=[port], daemon=True).start()
        Thread(target=self._update_statistics, daemon=True).start()

    def _read_credentials(self, client: SocketClient):
        # receive login information
        login_message = client.read_json()
        if not login_message:
            return None

        username = login_message["username"]
        client.username = username

        validate_email(username)
        return username.split("@")[0]

    def _login(self, username: str, client: SocketClient):
        with self._L_clients:
            self._logout(username)  # logout possible previous client
            self._logged_clients[username] = client

            with self._L_collection:
                self._ensure_default(username, "accepted_command_count", 0)
                self._ensure_default(username, "declined_command_count", 0)
                self._ensure_default(username, "total_seconds", 0)
                self._ensure_default(username, "portfolio_value", INITIAL_AMOUNT)
                self._ensure_default(username, "portfolio_state", get_initial_portfolio_state())

            print(f"logged in: {username}")

    def _logout(self, username: str):
        with self._L_clients:
            client = self._logged_clients.pop(username, None)
            if client:
                print(f"Logout: {username}")
                client.disconnect()

    def _update_statistics(self):
        i = 0
        while True:
            i += 1
            current_time = time.time()
            extra_time = current_time - self._last_time_check
            self._last_time_check = current_time

            values = []
            with self._L_collection:
                for user_data in self._collection.users.find({}):
                    username = user_data["_id"]
                    # calculate current value
                    try:
                        portfolio = PortfolioController(self._market, user_data["portfolio_state"])
                        value = portfolio.total_value.amount
                    except:
                        traceback.print_exc()
                        continue

                    update = {
                        "$set": {
                            "portfolio_value": value
                        }
                    }

                    if self.is_user_online(username):
                        update["$inc"] = {"total_seconds": extra_time}

                    # update time and value
                    self._collection.users.update({"_id": username}, update)
                    values.append((username, value))

            if i % 10 == 0:
                # log portfolio values
                self._collection.portfolio_values.insert({
                    "timestamp": time.time(),
                    "portfolio_values": values
                })

            time.sleep(1)

    def _ensure_default(self, username, field, value):
        with self._L_collection:
            if not self._collection.users.find_one({"_id": username}):
                self._collection.users.insert({"_id": username})

            self._collection.users.update({"_id": username, field: {"$exists": False}},
                                          {"$set": {field: value}})

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
        socket.setblocking(False)
        client = SocketClient(socket)
        username = None
        try:
            username = self._read_credentials(client)
            if not username:
                print(f"username is missing")
                return

            pairs_info = {}
            for pair, storage in self._storages.items():
                pairs_info[pair] = {
                    "entry_count": storage.get_entry_count()
                }

            client.send_json({
                "pairs_info": pairs_info
            })

            self._login(username, client)

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

                elif c == "receive_portfolio_state":
                    user_data = self._get_user_data(username)
                    response["portfolio_state"] = user_data["portfolio_state"]

                elif c == "update_portfolio_state":
                    update_command = jsonpickle.loads(command["update_command"])
                    with self._L_collection:
                        user_data = self._get_user_data(username)
                        state = deepcopy(user_data["portfolio_state"])
                        try:
                            update_result = update_command.apply(state, self._market)
                            db_update = {
                                "$set": {
                                    "portfolio_state": state
                                },
                                "$inc": {
                                    "accepted_command_count": 1
                                }
                            }

                            self._collection.transfers.insert({
                                "username": username,
                                "real_time": time.time(),
                                "market_timestamp": self._market.current_time,
                                "update_result": update_result
                            })

                            response["accepted"] = True
                            response["portfolio_state"] = state

                        except:
                            traceback.print_exc()
                            db_update = {
                                "$inc": {
                                    "declined_command_count": 1
                                }
                            }

                        self._collection.users.update(
                            {"_id": username},
                            db_update
                        )

                else:
                    raise AssertionError(f"Unknown command received: {command}")

                client.send_json(response)

        except:
            traceback.print_exc()
            print(f"Exception for {addr}")
        finally:
            if username:
                with self._L_clients:
                    if self._logged_clients.get(username) == client:
                        # if this socket client is still logged, log it out
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

    def _get_user_data(self, username):
        with self._L_collection:
            return self._collection.users.find_one({"_id": username})

    def _run_market(self):
        self._market.run()
