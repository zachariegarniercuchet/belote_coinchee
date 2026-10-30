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

from belote.bots import DEFAULT_BOT_ID, is_valid_bot, list_bots

SEATS = (0, 1, 2, 3, "board")
PLAYER_SEATS = (0, 1, 2, 3)

# Échiquiers de temps proposés dans le salon, en secondes. 0 = illimité.
# Les deux listes servent de liste blanche côté serveur et de propositions
# côté client : le sélecteur du lobby est construit à partir d'ici.
MOVE_TIME_PRESETS = (0, 10, 20, 30, 45, 60, 90)
TOTAL_TIME_PRESETS = (0, 120, 300, 600, 900, 1200, 1800)


def _preset_or_none(value, presets) -> int | None:
    """Ramène une valeur reçue du client à un preset autorisé, sinon None."""
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        return None
    return seconds if seconds in presets else None

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
    def __init__(self, code: str, visibility: str = "public"):
        self.code = code
        self.created_at = time.time()
        self.lock = threading.RLock()
        self.seats: dict = {s: Seat() for s in SEATS}
        self.game_session = None  # web.game_session.GameSession, une fois la partie lancée
        self.target_score = 1000
        # Échiquier de temps choisi dans le salon, en secondes (0 = illimité).
        # Décompté uniquement pendant la réflexion des joueurs humains.
        self.move_time_limit = 0
        self.total_time_limit = 0
        # "public" : la salle figure dans la liste d'accueil et accepte des
        # spectateurs pendant la partie. "private" : accès par code seul,
        # aucun spectateur, comportement d'origine.
        self.visibility = visibility if visibility in ("public", "private") else "public"
        # sid -> prénom des connections connectées sans siège (spectateurs).
        # Un spectateur ne reçoit aucune main et ne peut jouer qu'en reprenant
        # un siège de bot, entre deux donnes.
        self.spectators: dict[str, str] = {}
        # Reprises de siège en attente : siège -> (sid, prénom). Posées par un
        # spectateur entre deux donnes, appliquées au début de la donne suivante.
        self.pending_takeovers: dict[int, tuple[str, str]] = {}
        # Bot choisi par siège (siège vide au démarrage -> rempli par ce bot).
        # Modifiable depuis le lobby par n'importe quel membre du salon.
        self.bot_choices: dict[int, str] = {p: DEFAULT_BOT_ID for p in PLAYER_SEATS}

    def set_bot_choice(self, seat_key, bot_id: str) -> bool:
        """Mémorise le bot qui occupera `seat_key` si un humain ne le prend pas."""
        with self.lock:
            if seat_key not in PLAYER_SEATS:
                return False
            if self.seats[seat_key].occupied:
                return False
            if not is_valid_bot(bot_id):
                return False
            self.bot_choices[seat_key] = bot_id
            return True

    def set_time_control(self, move_seconds, total_seconds) -> bool:
        """Choisit l'échiquier de temps du salon, avant le démarrage de la partie.

        Les deux valeurs doivent figurer dans les presets ; sinon rien ne change.
        """
        move = _preset_or_none(move_seconds, MOVE_TIME_PRESETS)
        total = _preset_or_none(total_seconds, TOTAL_TIME_PRESETS)
        if move is None or total is None:
            return False
        with self.lock:
            if self.game_session is not None and not self.game_session.finished:
                return False  # partie en cours : réglages verrouillés
            self.move_time_limit = move
            self.total_time_limit = total
            return True

    def sid_of_seat(self, seat) -> str | None:
        """Sid de la connection actuellement installée à `seat`, s'il y en a une."""
        with self.lock:
            slot = self.seats.get(seat)
            return slot.sid if slot is not None else None

    def release_seat_to_bot(self, seat, bot_id: str) -> str | None:
        """Dépossède un joueur humain de son siège (temps total épuisé).

        Le siège redevient vide : c'est `bot_id` qui y joue désormais, et le
        lobby affiche son sélecteur de bot habituel. La connection dépossédée
        passe spectatrice. Retourne son sid (None s'il n'y en avait pas).
        """
        if seat not in PLAYER_SEATS:
            return None
        with self.lock:
            slot = self.seats[seat]
            sid, name = slot.sid, slot.name
            slot.sid = None
            slot.name = None
            if is_valid_bot(bot_id):
                self.bot_choices[seat] = bot_id
            if sid is not None:
                self.spectators[sid] = name or "Spectateur"
            return sid

    def add_spectator(self, sid: str, name: str) -> None:
        """Inscrit une connection sans siège comme spectateur du salon.

        Un salon privé ne connaît pas de spectateurs : il garde son
        comportement d'origine (accès par code, sièges verrouillés en partie).
        """
        with self.lock:
            if self.visibility != "public":
                return
            self.spectators[sid] = name

    def remove_spectator(self, sid: str) -> None:
        with self.lock:
            self.spectators.pop(sid, None)
            # Une demande de reprise ne doit pas survivre à son demandeur.
            for seat in [s for s, (s_sid, _n) in self.pending_takeovers.items() if s_sid == sid]:
                del self.pending_takeovers[seat]

    def spectator_count(self) -> int:
        with self.lock:
            return len(self.spectators)

    def pending_takeover_of(self, seat) -> tuple[str, str] | None:
        with self.lock:
            return self.pending_takeovers.get(seat)

    def pending_takeovers_snapshot(self) -> dict[int, str]:
        """{siège: prénom} des reprises en attente, lu en une seule prise de verrou."""
        with self.lock:
            return {seat: name for seat, (_sid, name) in self.pending_takeovers.items()}

    def request_takeover(self, seat, sid: str, name: str) -> bool:
        """Réserve un siège de bot pour un spectateur, à prendre à la donne suivante.

        Le siège reste occupé par son bot jusqu'au début de la donne suivante :
        la partie en cours n'est jamais interrompue.
        """
        with self.lock:
            if self.visibility != "public":
                return False
            if seat not in PLAYER_SEATS:
                return False
            if self.seats[seat].occupied:
                return False  # déjà pris par un humain
            holder = self.pending_takeovers.get(seat)
            if holder is not None and holder[0] != sid:
                return False  # un autre spectateur l'a déjà réservé
            self.pending_takeovers[seat] = (sid, name)
            return True

    def apply_takeovers(self) -> list[tuple[int, str, str]]:
        """Passe les reprises en attente au statut de siège occupé.

        Retourne [(siège, sid, prénom)] pour que la session puisse remplacer le
        bot par un joueur web. Le verrou couvre toute la permutation.
        """
        with self.lock:
            taken = list(self.pending_takeovers.items())
            self.pending_takeovers = {}
            for seat, (sid, name) in taken:
                slot = self.seats[seat]
                slot.sid = sid
                slot.name = name
                self.spectators.pop(sid, None)
            return [(seat, sid, name) for seat, (sid, name) in taken]

    def lobby_state(self, viewer_sid: str | None = None) -> dict:
        with self.lock:
            return {
                "code": self.code,
                "visibility": self.visibility,
                "your_seat": self.seat_of_sid(viewer_sid) if viewer_sid is not None else None,
                "seats": {
                    str(s): {"name": seat.name, "connected": seat.sid is not None}
                    for s, seat in self.seats.items()
                },
                "target_score": self.target_score,
                "move_time_limit": self.move_time_limit,
                "total_time_limit": self.total_time_limit,
                "move_time_presets": list(MOVE_TIME_PRESETS),
                "total_time_presets": list(TOTAL_TIME_PRESETS),
                "bot_choices": {str(p): self.bot_choices[p] for p in PLAYER_SEATS},
                "available_bots": list_bots(),
                "spectator_count": len(self.spectators),
                "pending_takeovers": {str(seat): name for seat, name
                                      in self.pending_takeovers_snapshot().items()},
                "game_in_progress": self.game_session is not None and not self.game_session.finished,
                "game_over": self.game_session is not None and self.game_session.finished,
            }

    def take_seat(self, seat_key, sid: str, name: str) -> bool:
        with self.lock:
            seat = self.seats.get(seat_key)
            if seat is None:
                return False
            # Un homonyme connecté n'est pas le propriétaire du siège.
            # Un siège déconnecté reste réservé à son nom pour la reconnexion.
            if seat.occupied and seat.sid != sid and (seat.sid is not None or seat.name != name):
                return False
            if (self.game_session and not self.game_session.finished
                    and (not seat.occupied or seat.name != name)):
                return False
            # Vérifier la destination AVANT de libérer l'ancien siège. Le verrou
            # couvre tout le déplacement, y compris deux demandes simultanées.
            for s in self.seats.values():
                if s.sid == sid:
                    s.sid = None
                    s.name = None
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

    def create_room(self, visibility: str = "public") -> Room:
        with self._lock:
            code = self._generate_code()
            room = Room(code, visibility=visibility)
            self._rooms[code] = room
            return room

    def public_rooms(self) -> list[dict]:
        """Annuaire des salons publics, pour l'écran d'accueil.

        Un salon privé n'y figure jamais. Le résultat ne contient aucune main
        ni information de jeu : uniquement le remplissage et l'avancement.
        """
        with self._lock:
            candidates = [room for room in self._rooms.values() if room.visibility == "public"]
        listing = []
        for room in candidates:
            with room.lock:
                if room.game_session is None:
                    phase = "lobby"
                elif room.game_session.finished:
                    phase = "finished"
                else:
                    phase = "playing"
                listing.append({
                    "code": room.code,
                    "phase": phase,
                    "target_score": room.target_score,
                    "player_count": sum(1 for p in PLAYER_SEATS if room.seats[p].occupied),
                    "spectator_count": len(room.spectators),
                })
        # Les salons libres d'abord, puis ceux en partie ; code croissant ensuite.
        return sorted(listing, key=lambda r: (r["phase"] != "lobby", r["code"]))

    def get(self, code: str) -> Room | None:
        if not code:
            return None
        with self._lock:
            return self._rooms.get(code.upper())

    def remove(self, code: str) -> None:
        with self._lock:
            self._rooms.pop(code.upper(), None)
