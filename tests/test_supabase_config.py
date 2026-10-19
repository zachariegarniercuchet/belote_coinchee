"""Configuration Supabase du frontend : injection des clés publiques et service de auth.js.

Le mode invité doit survivre à l'absence de configuration : ni clé, ni script
d'authentification, et la page reste jouable telle quelle.
"""

import os
import unittest
from unittest.mock import patch

import server

SUPABASE_ENV = {"SUPABASE_URL": "https://exemple.supabase.co", "SUPABASE_ANON_KEY": "cle-anon"}
EMPTY_ENV = {"SUPABASE_URL": "", "SUPABASE_ANON_KEY": ""}


class SupabaseConfigTests(unittest.TestCase):
    def test_index_renders_public_config_when_env_is_set(self):
        with patch.dict(os.environ, SUPABASE_ENV):
            page = server.app.test_client().get("/").get_data(as_text=True)
        self.assertIn("window.BELOTE_SUPABASE", page)
        self.assertIn("https://exemple.supabase.co", page)
        self.assertIn("cle-anon", page)

    def test_index_stays_guest_only_without_env(self):
        with patch.dict(os.environ, EMPTY_ENV):
            page = server.app.test_client().get("/?code=K7qm").get_data(as_text=True)
        self.assertIn('window.BELOTE_SUPABASE = {"anonKey": "", "url": ""}', page)
        self.assertIn('value="K7QM"', page)

    def test_auth_script_is_served_and_whitelisted(self):
        client = server.app.test_client()
        served = client.get("/static/auth.js")
        self.assertEqual(served.status_code, 200)
        self.assertIn("BeloteAuth", served.get_data(as_text=True))
        served.close()
        self.assertEqual(client.get("/static/secret.js").status_code, 404)


if __name__ == "__main__":
    unittest.main()
