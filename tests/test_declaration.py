"""Déclaration temporaire de fin de partie : déclencheur, envoi, reconnexion."""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from game_session import GameSession
from rooms import RoomManager
import server


def finish(session):
    """Fait terminer la partie sans la jouer : run() diffuse game_end puis le popup."""
    session.game = SimpleNamespace(finished=True, winner_team=0, target_score=1000,
                                   cumulative_scores={0: 0, 1: 0}, donne_logs=[])
    session.run()


def received(client, event):
    return [m["args"][0] for m in client.get_received() if m["name"] == event]


class DeclarationTests(unittest.TestCase):
    def test_offer_send_and_reconnect_delivery(self):
        handle, path = tempfile.mkstemp(suffix=".txt")
        with os.fdopen(handle, "w", encoding="utf-8") as file:
            file.write("Je t'aime, pour toujours.")
        self.addCleanup(os.remove, path)
        with patch.object(server, "rooms", RoomManager()), \
                patch.object(server, "sid_info", {}), \
                patch("declaration.DECLARATION_PATH", path):
            zach = server.socketio.test_client(server.app)
            partner = server.socketio.test_client(server.app)
            try:
                zach.emit("create_room", {"name": "Zacharie"})
                code = next(m["args"][0]["code"] for m in zach.get_received()
                            if m["name"] == "room_created")
                room = server.rooms.get(code)
                partner.emit("join_lobby", {"code": code, "name": "Éloïse"})
                zach.emit("take_seat", {"code": code, "seat": 0})
                partner.emit("take_seat", {"code": code, "seat": 1})

                # Fin de partie : le popup part vers Zacharie seul.
                session = GameSession(room, 1000, fill_bots=True)
                room.game_session = session
                finish(session)
                self.assertEqual([m["code"] for m in received(zach, "declaration_ask")], [code])
                self.assertEqual(received(partner, "declaration_ask"), [])

                # La partenaire est hors ligne au moment de l'envoi.
                partner.disconnect()
                zach.emit("declaration_reply", {"code": code, "accept": True})
                self.assertEqual([m["code"] for m in received(zach, "declaration_sent")], [code])
                self.assertEqual(received(zach, "error_message"), [])
                self.assertEqual(room.declaration_pending, "Je t'aime, pour toujours.")

                # À sa reconnexion, le texte plein écran lui parvient.
                partner = server.socketio.test_client(server.app)
                partner.emit("join_lobby", {"code": code, "name": "Éloïse"})
                shown = received(partner, "declaration_show")
                self.assertEqual([(m["code"], m["text"]) for m in shown],
                                 [(code, "Je t'aime, pour toujours.")])

                # Elle ferme : plus rien en attente, pas de rejeu au rechargement.
                partner.emit("declaration_closed", {"code": code})
                self.assertIsNone(room.declaration_pending)
                partner.emit("request_state", {"code": code})
                partner.emit("join_lobby", {"code": code, "name": "Éloïse"})
                self.assertEqual(received(partner, "declaration_show"), [])

                # Une réponse dupliquée de Zacharie ne renvoie rien.
                zach.emit("declaration_reply", {"code": code, "accept": True})
                self.assertIsNone(room.declaration_pending)

                # Partie suivante : on redemande, et le refus n'envoie rien.
                session2 = GameSession(room, 1000, fill_bots=True)
                room.game_session = session2
                finish(session2)
                self.assertEqual(len(received(zach, "declaration_ask")), 1)
                zach.emit("declaration_reply", {"code": code, "accept": False})
                self.assertIsNone(room.declaration_pending)
                self.assertEqual(received(partner, "declaration_show"), [])
            finally:
                zach.disconnect()
                partner.disconnect()

    def test_prompt_needs_exactly_two_humans_and_zacharie(self):
        with patch.object(server, "rooms", RoomManager()), patch.object(server, "sid_info", {}):
            zach = server.socketio.test_client(server.app)
            others = [server.socketio.test_client(server.app) for _ in range(3)]
            try:
                # Trois humains, dont Zacharie : pas de popup.
                zach.emit("create_room", {"name": "Zacharie"})
                code = next(m["args"][0]["code"] for m in zach.get_received()
                            if m["name"] == "room_created")
                room = server.rooms.get(code)
                others[0].emit("join_lobby", {"code": code, "name": "Éloïse"})
                others[1].emit("join_lobby", {"code": code, "name": "Bob"})
                zach.emit("take_seat", {"code": code, "seat": 0})
                others[0].emit("take_seat", {"code": code, "seat": 1})
                others[1].emit("take_seat", {"code": code, "seat": 2})
                session = GameSession(room, 1000, fill_bots=True)
                room.game_session = session
                finish(session)
                self.assertEqual(received(zach, "declaration_ask"), [])

                # Deux humains sans Zacharie : pas de popup.
                zach.emit("create_room", {"name": "Zach"})
                code = next(m["args"][0]["code"] for m in zach.get_received()
                            if m["name"] == "room_created")
                room = server.rooms.get(code)
                others[2].emit("join_lobby", {"code": code, "name": "Éloïse"})
                zach.emit("take_seat", {"code": code, "seat": 0})
                others[2].emit("take_seat", {"code": code, "seat": 1})
                session = GameSession(room, 1000, fill_bots=True)
                room.game_session = session
                finish(session)
                self.assertEqual(received(zach, "declaration_ask"), [])
            finally:
                zach.disconnect()
                for client in others:
                    client.disconnect()


if __name__ == "__main__":
    unittest.main()
