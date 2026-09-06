"""
Serveur web pour jouer à la belote coinchée en réseau local (LAN) :
- une personne lance ce serveur sur son ordinateur,
- les autres joueurs rejoignent depuis leur téléphone connecté au même Wi-Fi,
  soit en scannant un QR code, soit en tapant un code à 4 caractères,
- dans le salon (room), chacun choisit un siège parmi les 4 joueurs, ou le
  siège "plateau" (board) réservé à un appareil qui affiche juste la table
  (ex. une tablette posée au centre).

Lancer :
    python server.py
puis ouvrir l'adresse affichée dans le terminal sur l'ordinateur, et le
QR code affiché dans le salon depuis les téléphones (même réseau Wi-Fi).
"""

from __future__ import annotations

import io
import os
import socket
import sys
import threading

# Permet `import belote` quel que soit le répertoire
# depuis lequel ce script est lancé.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import qrcode
from flask import Flask, abort, jsonify, render_template, request, send_file, send_from_directory
from flask_socketio import join_room as sio_join_room

from extensions import socketio
from game_session import GameSession
from rooms import PLAYER_SEATS, RoomManager

app = Flask(__name__, template_folder=".", static_folder=None)
app.config["SECRET_KEY"] = os.environ.get("BELOTE_SECRET", "belote-coinchee-local-secret")
socketio.init_app(app)

rooms = RoomManager()

# sid -> {"code": str, "name": str} ; sert au nettoyage à la déconnexion et à
# la reconnexion (retrouver le même siège après une perte de wifi par ex.).
sid_info: dict[str, dict] = {}
sid_lock = threading.Lock()


def get_lan_ip() -> str:
    """Meilleure estimation de l'IP locale sur le réseau Wi-Fi (aucun paquet réellement envoyé)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


LAN_IP = get_lan_ip()


# --------------------------------------------------------------------------
# Routes HTTP
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", prefill_code="")


@app.route("/static/<path:filename>", endpoint="static")
def static_assets(filename):
    if filename not in {"app.js", "style.css"}:
        abort(404)
    return send_from_directory(PROJECT_ROOT, filename)


@app.route("/join/<code>")
def join_page(code):
    return render_template("index.html", prefill_code=code.upper())


@app.route("/room/<code>/info")
def room_info(code):
    room = rooms.get(code)
    if not room:
        abort(404)
    port = request.host.split(":")[1] if ":" in request.host else "80"
    return jsonify({"code": room.code, "join_url": f"http://{LAN_IP}:{port}/join/{room.code}"})


@app.route("/room/<code>/qr.png")
def room_qr(code):
    room = rooms.get(code)
    if not room:
        abort(404)
    port = request.host.split(":")[1] if ":" in request.host else "80"
    url = f"http://{LAN_IP}:{port}/join/{room.code}"
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


# --------------------------------------------------------------------------
# Socket.IO — salon / lobby
# --------------------------------------------------------------------------

def _emit_lobby_update(room):
    socketio.emit("lobby_update", room.lobby_state(), room=room.code)


def _seat_key(raw):
    if raw in (0, 1, 2, 3, "0", "1", "2", "3"):
        return int(raw)
    return "board"


@socketio.on("create_room")
def on_create_room(data):
    name = ((data or {}).get("name") or "").strip()[:20] or "Hôte"
    room = rooms.create_room()
    sio_join_room(room.code)
    with sid_lock:
        sid_info[request.sid] = {"code": room.code, "name": name}
    socketio.emit("room_created", {"code": room.code, "name": name}, to=request.sid)
    _emit_lobby_update(room)


@socketio.on("join_lobby")
def on_join_lobby(data):
    code = ((data or {}).get("code") or "").strip().upper()
    name = ((data or {}).get("name") or "").strip()[:20] or "Joueur"
    room = rooms.get(code)
    if not room:
        socketio.emit("error_message", {"message": "Ce salon n'existe pas. Vérifie le code."}, to=request.sid)
        return

    sio_join_room(room.code)
    with sid_lock:
        sid_info[request.sid] = {"code": room.code, "name": name}

    # Reconnexion : un siège porte déjà ce nom mais est actuellement sans connexion.
    with room.lock:
        for key, seat in room.seats.items():
            if seat.name == name and seat.sid is None:
                seat.sid = request.sid
                break

    socketio.emit("lobby_joined", room.lobby_state(), to=request.sid)
    _emit_lobby_update(room)
    if room.game_session:
        room.game_session.broadcast()


@socketio.on("take_seat")
def on_take_seat(data):
    code = (data or {}).get("code")
    room = rooms.get(code)
    if not room:
        return
    with sid_lock:
        info = sid_info.get(request.sid)
    name = info["name"] if info else "Joueur"
    seat_key = _seat_key((data or {}).get("seat"))

    ok = room.take_seat(seat_key, request.sid, name)
    if not ok:
        socketio.emit("error_message", {"message": "Ce siège est déjà occupé."}, to=request.sid)
        return
    _emit_lobby_update(room)
    if room.game_session:
        room.game_session.broadcast()


@socketio.on("leave_seat")
def on_leave_seat(data):
    code = (data or {}).get("code")
    room = rooms.get(code)
    if not room:
        return
    seat = room.seat_of_sid(request.sid)
    if seat is not None:
        room.free_seat(seat)
    _emit_lobby_update(room)


@socketio.on("start_game")
def on_start_game(data):
    code = (data or {}).get("code")
    room = rooms.get(code)
    if not room:
        return
    if room.game_session and not room.game_session.finished:
        return  # partie déjà en cours

    try:
        target_score = int((data or {}).get("target_score", 1000))
    except (TypeError, ValueError):
        target_score = 1000
    target_score = max(100, min(target_score, 5000))
    fill_bots = bool((data or {}).get("fill_bots", False))

    if not fill_bots and not room.players_ready():
        socketio.emit(
            "error_message",
            {"message": "Il faut 4 joueurs aux 4 sièges (ou coche « compléter avec des bots »)."},
            to=request.sid,
        )
        return

    room.target_score = target_score
    session = GameSession(room, target_score=target_score, fill_bots=True)
    room.game_session = session
    socketio.start_background_task(session.run)

    _emit_lobby_update(room)
    socketio.emit("game_started", {}, room=room.code)


@socketio.on("bid_choice")
def on_bid_choice(data):
    room = rooms.get((data or {}).get("code"))
    if not room or not room.game_session:
        return
    seat = room.seat_of_sid(request.sid)
    if seat not in PLAYER_SEATS:
        return
    try:
        index = int((data or {}).get("index"))
    except (TypeError, ValueError):
        return
    room.game_session.submit_bid(seat, index)


@socketio.on("play_card")
def on_play_card(data):
    room = rooms.get((data or {}).get("code"))
    if not room or not room.game_session:
        return
    seat = room.seat_of_sid(request.sid)
    if seat not in PLAYER_SEATS:
        return
    card_id = (data or {}).get("card_id")
    if not card_id:
        return
    room.game_session.submit_card(seat, card_id)


@socketio.on("request_state")
def on_request_state(data):
    room = rooms.get((data or {}).get("code"))
    if not room:
        return
    if room.game_session:
        room.game_session.broadcast()
    else:
        socketio.emit("lobby_update", room.lobby_state(), to=request.sid)


@socketio.on("dismiss_recap")
def on_dismiss_recap(data):
    room = rooms.get((data or {}).get("code"))
    if room and room.game_session:
        room.game_session.dismiss_recap()


@socketio.on("new_game")
def on_new_game(data):
    room = rooms.get((data or {}).get("code"))
    if not room:
        return
    if room.game_session and room.game_session.finished:
        room.game_session = None
    _emit_lobby_update(room)


@socketio.on("disconnect")
def on_disconnect():
    with sid_lock:
        info = sid_info.pop(request.sid, None)
    if not info:
        return
    room = rooms.get(info["code"])
    if not room:
        return
    # On ne libère pas le nom du siège : juste le sid, pour permettre une
    # reconnexion rapide (perte wifi, verrouillage d'écran...).
    with room.lock:
        for seat in room.seats.values():
            if seat.sid == request.sid:
                seat.sid = None
    _emit_lobby_update(room)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("  Belote Coinchée — serveur local")
    print("=" * 60)
    print(f"  Sur cet ordinateur : http://localhost:{port}")
    print(f"  Depuis un téléphone sur le même Wi-Fi : http://{LAN_IP}:{port}")
    print("=" * 60)
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)