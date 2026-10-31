"""Lien de partage et QR code d'un salon.

Le lien encodé dans le QR code doit viser le serveur public déployé (Render),
jamais l'IP locale du conteneur, tout en gardant l'IP Wi-Fi quand le serveur
tourne sur un ordinateur du réseau.

Lancer depuis la racine : python -B -m unittest discover -s tests -p test_room_links.py
Nécessite les dépendances web de requirements.txt.
"""

import io
import unittest
from unittest.mock import patch

import qrcode

from rooms import RoomManager
import server


class RoomShareLinkTests(unittest.TestCase):
    def setUp(self):
        rooms = patch.object(server, "rooms", RoomManager())
        sid_info = patch.object(server, "sid_info", {})
        rooms.start()
        sid_info.start()
        self.addCleanup(rooms.stop)
        self.addCleanup(sid_info.stop)

        client = server.socketio.test_client(server.app)
        client.emit("create_room", {"name": "Zoé"})
        created = [m["args"][0] for m in client.get_received() if m["name"] == "room_created"][-1]
        self.code = created["code"]
        self.client = server.app.test_client()

    def expected_png(self, url: str) -> bytes:
        buf = io.BytesIO()
        qrcode.make(url, box_size=8, border=2).save(buf, format="PNG")
        return buf.getvalue()

    def test_qr_code_points_to_the_deployed_server(self):
        # Comme Render : hôte public, schéma porté par X-Forwarded-Proto.
        base_url = "http://belote-coinchee-g77g.onrender.com/"
        headers = {"X-Forwarded-Proto": "https"}
        join_url = f"https://belote-coinchee-g77g.onrender.com/?code={self.code}"

        info = self.client.get(f"/room/{self.code}/info",
                               base_url=base_url, headers=headers)
        self.assertEqual(info.status_code, 200)
        self.assertEqual(info.get_json()["join_url"], join_url)

        png = self.client.get(f"/room/{self.code}/qr.png",
                              base_url=base_url, headers=headers)
        self.assertEqual(png.status_code, 200)
        self.assertEqual(png.mimetype, "image/png")
        # Le PNG doit encoder exactement l'URL de rejoignage attendue.
        self.assertEqual(png.data, self.expected_png(join_url))

    def test_qr_code_keeps_the_lan_url_locally_and_honours_the_override(self):
        lan_url = f"http://{server.LAN_IP}:5000/?code={self.code}"

        info = self.client.get(f"/room/{self.code}/info",
                               base_url="http://127.0.0.1:5000/")
        self.assertEqual(info.status_code, 200)
        self.assertEqual(info.get_json()["join_url"], lan_url)

        png = self.client.get(f"/room/{self.code}/qr.png",
                              base_url="http://127.0.0.1:5000/")
        self.assertEqual(png.data, self.expected_png(lan_url))

        with patch.object(server, "PUBLIC_BASE_URL", "https://partage.example"):
            info = self.client.get(f"/room/{self.code}/info",
                                   base_url="http://127.0.0.1:5000/")
            self.assertEqual(info.get_json()["join_url"],
                             f"https://partage.example/?code={self.code}")


if __name__ == "__main__":
    unittest.main()
