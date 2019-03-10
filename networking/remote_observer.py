from typing import List, Dict

from networking.remote_entry_reader import RemoteEntryReader
from networking.socket_client import SocketClient


class RemoteObserver(object):
    def __init__(self, pairs: List[str], remote_endpoint: str, username: str, password: str):
        self._pairs = list(pairs)
        self._remote_endpoint = remote_endpoint
        self._username = username
        self._password = password

        self._readers: Dict[str, RemoteEntryReader] = {}

        self._client: SocketClient = None

    def get_reader(self, pair):
        return self._readers.get(pair)

    def connect(self):
        self._client = self._create_socket_client(self._remote_endpoint, self._username, self._password)

        initial_message = self._client.read_json()
        pairs_info = initial_message["pairs_info"]

        for pair in self._pairs:
            pair_info = pairs_info[pair]

            self._readers[pair] = RemoteEntryReader(pair, pair_info, self)

        raise NotImplementedError("spin up reader thread")

    def _create_socket_client(self, remote_host: str, username: str, password: str) -> SocketClient:
        raise NotImplementedError()

    def _client_reader(self):
        while True:
            message = self._client.read_bytes()
            raise NotImplementedError()
