import json
import socket
from typing import Dict, Tuple





class JsonLinePeer:
    """Prosty peer TCP wysylajacy i odbierajacy po jednym obiekcie JSON na linie."""

    def __init__(self, conn: socket.socket):
        self.conn = conn
        self.file = conn.makefile("rwb")

    def send(self, message: Dict) -> None:
        data = (json.dumps(message, separators=(",", ":")) + "\n").encode("utf-8")
        self.file.write(data)
        self.file.flush()

    def recv(self) -> Dict:
        line = self.file.readline()
        if not line:
            raise ConnectionError("Polaczenie zamkniete")
        return json.loads(line.decode("utf-8"))

    def close(self) -> None:
        self.file.close()
        self.conn.close()


def wait_for_client(host: str, port: int) -> Tuple[JsonLinePeer, Tuple[str, int]]:
    """Czeka na jednego klienta TCP i zwraca peer JSONL oraz adres klienta."""
    server = socket.create_server((host, port))
    try:
        conn, address = server.accept()
        return JsonLinePeer(conn), address
    finally:
        server.close()


def connect_to_server(host: str, port: int) -> JsonLinePeer:
    """Laczy sie z serwerem TCP i opakowuje socket jako peer JSONL."""
    return JsonLinePeer(socket.create_connection((host, port)))