"""
Gestion des salons (rooms) : code, sièges (4 joueurs + 1 "plateau" optionnel),
et association avec une partie en cours (GameSession).

Ce module ne connaît rien de Flask/Socket.IO ni des règles de belote : c'est
juste l'état partagé, protégé par un verrou pour l'accès concurrent (chaque
event Socket.IO en mode threading tourne dans son propre thread).
"""

from __future__ import annotations

import random
import string
import threading
import time

SEATS = (0, 1, 2, 3, "board")
PLAYER_SEATS = (0, 1, 2, 3)

# Caractères sans ambiguïté visuelle (pas de O/0, I/1) pour un code lisible à l'oral.
CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


class Seat:
    __slots__ = ("sid", "name")

    def __init__(self, sid: str | None = None, name: str | None = None):
        self.sid = sid
        self.name = name

    @property
    def occupied(self) -> bool:
        return self.name is not None


class Room:
    def __init__(self, code: str):
        self.code = code
        self.created_at = time.time()
        self.lock = threading.RLock()
        self.seats: dict = {s: Seat() for s in SEATS}
        self.game_session = None  # web.game_session.GameSession, une fois la partie lancée
        self.target_score = 1000

    def lobby_state(self) -> dict:
        with self.lock:
            return {
                "code": self.code,
                "seats": {
                    str(s): {"name": seat.name, "connected": seat.sid is not None}
                    for s, seat in self.seats.items()
                },
                "target_score": self.target_score,
                "game_in_progress": self.game_session is not None and not self.game_session.finished,
                "game_over": self.game_session is not None and self.game_session.finished,
            }

    def take_seat(self, seat_key, sid: str, name: str) -> bool:
        with self.lock:
            seat = self.seats.get(seat_key)
            if seat is None:
                return False
            if seat.occupied and seat.name != name:
                return False
            # Libère un éventuel autre siège que ce sid occupait déjà.
            for s in self.seats.values():
                if s.sid == sid:
                    s.sid = None
            seat.sid = sid
            seat.name = name
            return True

    def rebind_sid(self, seat_key, sid: str) -> None:
        """Reconnexion : on retrouve le même siège via le nom, on met juste à jour le sid."""
        with self.lock:
            seat = self.seats.get(seat_key)
            if seat is not None:
                seat.sid = sid

    def free_seat(self, seat_key) -> None:
        with self.lock:
            seat = self.seats.get(seat_key)
            if seat is not None:
                seat.sid = None
                seat.name = None

    def seat_of_sid(self, sid: str):
        with self.lock:
            for key, seat in self.seats.items():
                if seat.sid == sid:
                    return key
            return None

    def players_ready(self) -> bool:
        with self.lock:
            return all(self.seats[p].occupied for p in PLAYER_SEATS)


class RoomManager:
    def __init__(self):
        self._rooms: dict[str, Room] = {}
        self._lock = threading.RLock()

    def _generate_code(self, length: int = 4) -> str:
        while True:
            code = "".join(random.choice(CODE_ALPHABET) for _ in range(length))
            if code not in self._rooms:
                return code

    def create_room(self) -> Room:
        with self._lock:
            code = self._generate_code()
            room = Room(code)
            self._rooms[code] = room
            return room

    def get(self, code: str) -> Room | None:
        if not code:
            return None
        with self._lock:
            return self._rooms.get(code.upper())

    def remove(self, code: str) -> None:
        with self._lock:
            self._rooms.pop(code.upper(), None)