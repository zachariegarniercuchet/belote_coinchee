"""Parcours salon : changement de place, concurrence et reconnexion."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from belote.bidding import Contract
from belote.bots import DEFAULT_BOT_ID, create_bot, get_bot_name, list_bots
from belote.cards import Suit
from rooms import RoomManager
import server


class LobbyTests(unittest.TestCase):
    def test_seat_changes_conflicts_and_reconnection(self):
        with patch.object(server, "rooms", RoomManager()), patch.object(server, "sid_info", {}):
            clients = []

            def connect(name, code=None):
                client = server.socketio.test_client(server.app)
                clients.append(client)
                client.emit("join_lobby" if code else "create_room", {"code": code, "name": name})
                return client

            def latest(client, event="lobby_update"):
                return [message["args"][0] for message in client.get_received()
                        if message["name"] == event][-1]

            try:
                # Le même catalogue documente les versions et nomme les joueurs.
                http = server.app.test_client()
                catalog = http.get("/api/bots").get_json()
                portraits = set()
                for bot_info in catalog:
                    for field in ("family", "version", "author", "description"):
                        self.assertTrue(bot_info[field])
                    self.assertIn(bot_info["family"], bot_info["label"])
                    self.assertIn(bot_info["version"], bot_info["label"])
                    self.assertEqual(len(set(bot_info["names"])), 4)
                    self.assertEqual(bot_info["names"],
                                     [get_bot_name(bot_info["id"], seat) for seat in range(4)])
                    if bot_info["family"] == "de Belote":
                        self.assertEqual(bot_info["names"], ["Charles de Belote", "Aliénor de Belote",
                                                            "Octave de Belote", "Apolline de Belote"])
                    self.assertTrue(bot_info["theme"])
                    self.assertEqual(len(bot_info["avatars"]), 4)
                    self.assertTrue(all(avatar is None for avatar in bot_info["avatars"])
                                    or len(set(bot_info["avatars"])) == 4)
                    portraits.update(avatar for avatar in bot_info["avatars"] if avatar)
                    # All families share the same public contract/role interface.
                    player = create_bot(bot_info["id"], 0)
                    for team in (0, 1):
                        contract = Contract(player=team, team=team, points=90,
                                            suit=Suit.COEUR, is_capot=False)
                        player.notify_contract(contract)
                        self.assertIs(player.contract, contract)
                        self.assertEqual(player.is_attacking, team == 0)
                        self.assertEqual(player.is_defending, team == 1)
                    player.notify_donne_start()
                    self.assertIsNone(player.contract)
                    self.assertFalse(player.is_attacking or player.is_defending)
                for portrait in portraits:
                    with http.head("/assets/bots/" + portrait) as response:
                        self.assertEqual(response.status_code, 200)
                        self.assertEqual(response.mimetype, "image/png")
                self.assertEqual(http.get("/assets/bots/prompts.json").status_code, 404)
                alice = connect("Alice")
                code = latest(alice, "room_created")["code"]
                room = server.rooms.get(code)
                bob = connect("Bob", code)
                homonym = connect("Alice", code)
                bot = next(bot["id"] for bot in list_bots() if bot["id"] != DEFAULT_BOT_ID)
                alice.emit("set_bot", {"code": code, "seat": 0, "bot_id": bot})
                alice.emit("take_seat", {"code": code, "seat": 0})
                bob.emit("take_seat", {"code": code, "seat": 1})
                self.assertEqual(latest(alice)["your_seat"], 0)
                self.assertEqual(latest(bob)["your_seat"], 1)
                self.assertIsNone(latest(homonym)["your_seat"])

                # Même prénom : impossible de voler une place connectée.
                homonym.emit("take_seat", {"code": code, "seat": 0})
                self.assertIsNone(latest(homonym)["your_seat"])
                self.assertEqual(room.seats[0].name, "Alice")

                # Deux déplacements concurrents : un seul gagne, l'autre garde sa place.
                barrier = Barrier(2)

                def compete(client):
                    barrier.wait(timeout=5)
                    client.emit("take_seat", {"code": code, "seat": 2})

                with ThreadPoolExecutor(max_workers=2) as pool:
                    list(pool.map(compete, [alice, bob]))
                messages = [client.get_received() for client in (alice, bob)]
                states = [[message["args"][0] for message in received
                           if message["name"] == "lobby_update"][-1] for received in messages]
                self.assertEqual(sum(message["name"] == "error_message"
                                     for received in messages for message in received), 1)
                self.assertEqual(sum(state["your_seat"] == 2 for state in states), 1)
                for previous, state in enumerate(states):
                    self.assertIn(state["your_seat"], (previous, 2))
                self.assertEqual(sum(seat.occupied for seat in room.seats.values()), 2)
                for client, expected_name in ((alice, "Alice"), (bob, "Bob")):
                    self.assertEqual(sum(seat.name == expected_name for seat in room.seats.values()), 1)

                # Le bot configuré revient lorsque l'humain change de place.
                alice.emit("take_seat", {"code": code, "seat": "board"})
                state = latest(alice)
                self.assertEqual(state["your_seat"], "board")
                self.assertIsNone(state["seats"]["0"]["name"])
                self.assertEqual(state["bot_choices"]["0"], bot)
                alice.emit("leave_seat", {"code": code})
                self.assertIsNone(latest(alice)["your_seat"])
                alice.emit("take_seat", {"code": code, "seat": 0})

                # En partie, seul le siège existant peut être repris après déconnexion.
                preview = server.GameSession(room, target_score=1000)._build_common()
                self.assertEqual(set(preview["bot_profiles"]),
                                 {str(seat) for seat in range(4) if not room.seats[seat].occupied})
                for seat, profile in preview["bot_profiles"].items():
                    bot_info = next(bot for bot in catalog if bot["id"] == profile["id"])
                    self.assertEqual(profile["avatar"], bot_info["avatars"][int(seat)])
                room.game_session = SimpleNamespace(finished=False, broadcast=lambda: None)
                alice.emit("take_seat", {"code": code, "seat": 3})
                self.assertEqual(latest(alice)["your_seat"], 0)
                alice.emit("leave_seat", {"code": code})
                self.assertTrue(any(message["name"] == "error_message" for message in alice.get_received()))
                self.assertTrue(room.seats[0].occupied)
                alice.disconnect()
                reconnected = connect("Alice", code)
                self.assertEqual(latest(reconnected)["your_seat"], 0)
                reconnected.emit("take_seat", {"code": code, "seat": 0})
                self.assertEqual(latest(reconnected)["your_seat"], 0)
                self.assertEqual(sum(seat.name == "Alice" for seat in room.seats.values()), 1)
                room.game_session = None
                reconnected.emit("leave_seat", {"code": code})
                self.assertIsNone(latest(reconnected)["your_seat"])
            finally:
                for client in clients:
                    if client.is_connected():
                        client.disconnect()

    def test_stale_seat_is_reclaimed_by_session_token(self):
        """Un siège dont l'ancien sid n'est pas encore expiré est repris au jeton.

        iOS met Safari en veille sans fermer la WebSocket : le serveur détecte
        la déconnexion avec retard. Le joueur revient donc avec un nouveau sid
        alors que le siège porte encore l'ancien, et la reprise par prénom
        échoue. Sans jeton on reste spectateur (aucun homonyme ne doit voler la
        place) ; avec le jeton de l'onglet le siège est repris, et la
        déconnexion tardive de l'ancien sid ne doit pas le libérer.
        """
        with patch.object(server, "rooms", RoomManager()), patch.object(server, "sid_info", {}):
            clients = []

            def connect(name, code=None, token=None):
                client = server.socketio.test_client(server.app)
                clients.append(client)
                payload = {"name": name}
                if code:
                    payload["code"] = code
                if token:
                    payload["token"] = token
                client.emit("join_lobby" if code else "create_room", payload)
                return client

            def your_seat(client):
                states = [message["args"][0] for message in client.get_received()
                          if message["name"] in ("lobby_joined", "lobby_update")]
                return states[-1]["your_seat"] if states else "aucun état"

            try:
                host = connect("Alice")
                code = [message["args"][0] for message in host.get_received()
                        if message["name"] == "room_created"][-1]["code"]
                room = server.rooms.get(code)

                host.emit("take_seat", {"code": code, "seat": 0, "token": "jeton-A"})
                self.assertEqual(your_seat(host), 0)
                self.assertEqual(room.seats[0].token, "jeton-A")

                # L'ancienne connexion reste "vivante" : on ne la déconnecte pas.
                ancien_sid = room.seats[0].sid
                self.assertIsNotNone(ancien_sid)

                # Sans jeton : le siège est encore tenu, on devient spectateur.
                sans_jeton = connect("Alice", code)
                self.assertIsNone(your_seat(sans_jeton))
                self.assertEqual(room.seats[0].sid, ancien_sid)

                # Avec le jeton du même onglet : le siège est repris.
                avec_jeton = connect("Alice", code, token="jeton-A")
                self.assertEqual(your_seat(avec_jeton), 0)
                nouveau_sid = room.seats[0].sid
                self.assertNotEqual(nouveau_sid, ancien_sid)
                self.assertEqual(room.seats[0].name, "Alice")

                # La déconnexion tardive de l'ancien sid ne libère pas le siège.
                host.disconnect()
                self.assertEqual(room.seats[0].sid, nouveau_sid)
                self.assertTrue(room.seats[0].occupied)
            finally:
                for client in clients:
                    if client.is_connected():
                        client.disconnect()


if __name__ == "__main__":
    unittest.main()
