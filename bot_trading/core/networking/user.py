from typing import List

from bot_trading.core.networking.socket_client import SocketClient


class User(object):
    def __init__(self, username):
        self._username = username
        self._readonly_clients: List[SocketClient] = []
        self._write_client: SocketClient = None

    @property
    def is_online(self):
        return self._write_client is not None

    def accept(self, new_client):
        if new_client.is_readonly:
            self._readonly_clients.append(new_client)
            while len(self._readonly_clients) > 3:
                client = self._readonly_clients.pop(0)
                self._shutdown_client(client)
        else:
            if self._write_client is not None:
                self._shutdown_client(self._write_client)

            self._write_client = new_client

    def remove(self, client):
        if client in self._readonly_clients:
            self._readonly_clients.remove(client)

        if self._write_client is client:
            self._write_client = None

        self._shutdown_client(client)

    def broadcast(self, data: str):
        if self._write_client:
            self._write_client.send_string(data)

        for client in self._readonly_clients:
            client.send_string(data)

    def _shutdown_client(self, client):
        print(f"Shutdown: {self._username}, is_reaodnly: {client.is_readonly}, is_connected: {client.is_connected}")

        client.send_json({"system": "shutdown"})
        client.disconnect()
