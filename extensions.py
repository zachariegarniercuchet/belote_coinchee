import os

from flask_socketio import SocketIO

# Autorise le front (ex. GitHub Pages) a se connecter a ce backend depuis une
# autre origine. Par defaut "*" (tout le monde) pour rester simple ; en
# production, mettez plutot l URL exacte de votre front dans la variable
# d environnement CORS_ALLOWED_ORIGIN (ex. "https://votre-pseudo.github.io").
CORS_ALLOWED_ORIGIN = os.environ.get("CORS_ALLOWED_ORIGIN", "*")

socketio = SocketIO(async_mode="threading", cors_allowed_origins=CORS_ALLOWED_ORIGIN)
