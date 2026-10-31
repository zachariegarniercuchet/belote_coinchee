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
import ipaddress
import os
import socket
import sys
import threading
import time

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
from rooms import EMPTY_ROOM_IDLE, NO_HUMAN_IDLE, PLAYER_SEATS, RoomManager
from belote.bots import is_valid_bot, list_bots

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

# En local, on devine l'IP Wi-Fi pour que le QR code pointe vers le bon
# endroit. Une fois deploye (Render, etc.), l'adresse publique n'a plus
# rien a voir avec une IP locale : PUBLIC_BASE_URL (ex.
# "https://belote-coinchee-g77g.onrender.com") permet de forcer l'adresse,
# et a defaut l'URL est deduite de l'hote de la requete, ce qui convient a
# un deploiement comme a un acces par IP locale.
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")


def _split_host(host: str) -> tuple[str, str]:
    """Hôte et port séparés depuis `request.host` (IPv6 entre crochets)."""
    if host.startswith("["):  # "[::1]:5000"
        end = host.find("]")
        name, rest = host[1:end], host[end + 1:]
        return name, rest[1:] if rest.startswith(":") else ""
    if host.count(":") == 1:
        name, port = host.split(":")
        return name, port
    return host, ""


def _is_local_host(hostname: str) -> bool:
    """Vrai si l'hôte ne désigne que la machine ou le réseau local.

    Un QR code doit alors viser l'IP Wi-Fi du LAN. Un nom de domaine complet
    (« belote-coinchee-g77g.onrender.com », une IP publique) est considéré
    comme joignable tel quel, contrairement à « localhost » ou à un nom de
    poste sans point (« BUREAU »).
    """
    name = hostname.strip("[]").lower()
    if not name or name == "localhost" or name.endswith(".local"):
        return True
    try:
        addr = ipaddress.ip_address(name)
    except ValueError:
        return "." not in name
    return addr.is_loopback or addr.is_link_local or addr.is_private or addr.is_unspecified


def get_base_url(req) -> str:
    if PUBLIC_BASE_URL:
        return PUBLIC_BASE_URL
    hostname, port = _split_host(req.host)
    if _is_local_host(hostname):
        return f"http://{LAN_IP}:{port or '80'}"
    # Derrière un proxy (Render envoie X-Forwarded-Proto), l'hôte public est
    # déjà celui de la requête : on s'y fie plutôt que sur une IP locale.
    scheme = (req.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip() or req.scheme
    return f"{scheme}://{req.host}"


# --------------------------------------------------------------------------
# Routes HTTP
# --------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template(
        "index.html",
        prefill_code=request.args.get("code", "").upper(),
        supabase=supabase_config(),
    )


def supabase_config() -> dict:
    """Clés **publiques** Supabase injectées dans la page (comptes optionnels).

    Sans ces variables, le frontend reste exactement en mode invité et aucune
    interface de connexion n'est affichée. La clé anon est faite pour être
    publique : la protection des données vient des politiques RLS côté base,
    jamais d'une clé secrète dans le navigateur.
    """
    return {
        "url": os.environ.get("SUPABASE_URL", "").strip(),
        "anonKey": os.environ.get("SUPABASE_ANON_KEY", "").strip(),
    }


# Liste blanche des fichiers statiques servis : JS, CSS et icônes de la plateforme.
ALLOWED_STATIC_FILES = {
    "app.js",
    "auth.js",
    "style.css",
    "logo/apple-touch-icon.png",
    "logo/favicon-16x16.png",
    "logo/favicon-32x32.png",
}


@app.route("/static/<path:filename>", endpoint="static")
def static_assets(filename):
    if filename not in ALLOWED_STATIC_FILES:
        abort(404)
    return send_from_directory(PROJECT_ROOT, filename)


@app.route("/assets/bots/<filename>")
def bot_avatar(filename):
    allowed = {avatar for bot in list_bots() for avatar in bot["avatars"]}
    if filename not in allowed:
        abort(404)
    return send_from_directory(os.path.join(PROJECT_ROOT, "frontend-github-pages", "assets", "bots"),
                               filename, max_age=86400)


@app.route("/join/<code>")
def join_page(code):
    return render_template("index.html", prefill_code=code.upper(), supabase=supabase_config())


@app.route("/room/<code>/info")
def room_info(code):
    room = rooms.get(code)
    if not room:
        abort(404)
    return jsonify({"code": room.code, "join_url": f"{get_base_url(request)}/?code={room.code}"})


@app.route("/room/<code>/qr.png")
def room_qr(code):
    room = rooms.get(code)
    if not room:
        abort(404)
    url = f"{get_base_url(request)}/?code={room.code}"
    img = qrcode.make(url, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/api/bots")
def api_bots():
    """Catalogue des bots (pour le sélecteur du lobby)."""
    return jsonify(list_bots())


# --------------------------------------------------------------------------
# Socket.IO — salon / lobby
# --------------------------------------------------------------------------

def _emit_lobby_update(room):
    # Ne pas déduire le propriétaire d'un siège de son prénom (homonymes).
    with sid_lock:
        members = [sid for sid, info in sid_info.items() if info["code"] == room.code]
    with room.lock:
        for sid in members:
            socketio.emit("lobby_update", room.lobby_state(sid), to=sid)


def _seat_key(raw):
    if raw in (0, 1, 2, 3, "0", "1", "2", "3"):
        return int(raw)
    return "board"


def _room_has_human(code: str) -> bool:
    """Vrai si au moins une connection humaine pointe encore vers ce salon.

    `sid_info` est la source fiable : tout client connecté (joueur assis ou
    spectateur) y a une entrée dont `code` désigne son salon. On ne regarde
    pas les seats ni les spectateurs, qui peuvent garder un nom après une
    déconnexion le temps d'une reprise.
    """
    with sid_lock:
        return any(info["code"] == code for info in sid_info.values())


def purge_expired_rooms(now: float | None = None) -> list[str]:
    """Ferme les salons abandonnés et retourne leurs codes.

    Ne ferme jamais un salon :
    - avec une partie en cours (un humain peut encore y être, ou les bots
      jouent — on ne touche pas à un thread de jeu) ;
    - auquel au moins une connection humaine est encore attachée.

    Sinon, un salon « nu » (aucun siège occupé, aucune partie) est fermé au
    bout de `EMPTY_ROOM_IDLE`, et un salon qui a accueilli des joueurs ou une
    partie au bout de `NO_HUMAN_IDLE`, mesurés depuis la dernière activité
    humaine. La décision et la suppression se font sous le verrou de chaque
    salon puis celui du gestionnaire, pour ne pas fermer un salon qu'un
    humain vient de rejoindre.
    """
    now = time.time() if now is None else now
    closed: list[str] = []
    for room in rooms.all_rooms():
        with room.lock:
            # Partie en cours : jamais purgé (le thread de jeu continue).
            if room.game_session is not None and not room.game_session.finished:
                continue
            threshold = EMPTY_ROOM_IDLE if room.is_vacant() else NO_HUMAN_IDLE
            if room.idle_seconds(now) < threshold:
                continue
        # Re-vérifie l'absence d'humain juste avant suppression, puis ferme.
        if _room_has_human(room.code):
            continue
        rooms.remove(room.code)
        closed.append(room.code)
    return closed


def _purge_loop(interval: float = 60.0):
    """Tâche de fond : ferme périodiquement les salons abandonnés.

    Lance via `socketio.start_background_task` uniquement au démarrage réel du
    serveur (`__main__`), jamais à l'import, pour ne pas tourner dans les tests.
    """
    while True:
        time.sleep(interval)
        try:
            purge_expired_rooms()
        except Exception:
            # Une erreur de balayage ne doit jamais tuer la tâche de fond.
            pass


@socketio.on("create_room")
def on_create_room(data):
    name = ((data or {}).get("name") or "").strip()[:20] or "Hôte"
    # Salon public par défaut : figure dans l'annuaire et accepte des
    # spectateurs pendant la partie. Un salon privé reste accessible par code.
    visibility = ((data or {}).get("visibility") or "public").strip().lower()
    if visibility not in ("public", "private"):
        visibility = "public"
    room = rooms.create_room(visibility=visibility, created_by=name)
    sio_join_room(room.code)
    with sid_lock:
        sid_info[request.sid] = {"code": room.code, "name": name}
    socketio.emit("room_created", {"code": room.code, "name": name,
                                   "visibility": room.visibility}, to=request.sid)
    _emit_lobby_update(room)


@socketio.on("list_public_rooms")
def on_list_public_rooms(_data=None):
    """Annuaire des salons publics, envoyé uniquement au demandeur."""
    # On en profite pour fermer les salons abandonnés : l'annuaire reste propre
    # même sans tâche de fond, et un visiteur rafraîchit souvent la liste.
    purge_expired_rooms()
    socketio.emit("public_rooms", {"rooms": rooms.public_rooms()}, to=request.sid)


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
    room.touch()

    # Reconnexion : un siège porte déjà ce nom mais est actuellement sans connexion.
    with room.lock:
        if room.seat_of_sid(request.sid) is None:
            for seat in room.seats.values():
                if seat.name == name and seat.sid is None:
                    seat.sid = request.sid
                    break

    # Sans siège, on est spectateur : on suit le salon et la partie sans main.
    with room.lock:
        if room.seat_of_sid(request.sid) is None:
            room.add_spectator(request.sid, name)
        else:
            room.remove_spectator(request.sid)

    socketio.emit("lobby_joined", room.lobby_state(request.sid), to=request.sid)
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
        message = ("Les sièges sont verrouillés pendant la partie."
                   if room.game_session and not room.game_session.finished
                   else "Ce siège est déjà occupé. Ta place précédente est conservée.")
        socketio.emit("error_message", {"message": message}, to=request.sid)
        socketio.emit("lobby_update", room.lobby_state(request.sid), to=request.sid)
        return
    room.touch()
    _emit_lobby_update(room)
    room.remove_spectator(request.sid)
    if room.game_session:
        room.game_session.broadcast()


@socketio.on("leave_seat")
def on_leave_seat(data):
    code = (data or {}).get("code")
    room = rooms.get(code)
    if not room:
        return
    with room.lock:
        if room.game_session and not room.game_session.finished:
            socketio.emit("error_message", {"message": "Les sièges sont verrouillés pendant la partie."}, to=request.sid)
            return
        seat = room.seat_of_sid(request.sid)
        if seat is not None:
            room.free_seat(seat)
    room.touch()
    _emit_lobby_update(room)


@socketio.on("request_takeover")
def on_request_takeover(data):
    """Un spectateur réserve un siège de bot ; il prend place à la donne suivante.

    La donne en cours n'est jamais interrompue : la permutation est appliquée
    par GameSession au début de la donne suivante.
    """
    room = rooms.get((data or {}).get("code"))
    if not room:
        return
    session = room.game_session
    if not session or session.finished:
        return
    # Seul un spectateur peut monter à table ; un joueur déjà assis ne l'est pas.
    if room.seat_of_sid(request.sid) is not None:
        return
    with sid_lock:
        info = sid_info.get(request.sid)
    name = info["name"] if info else "Joueur"
    try:
        seat = int((data or {}).get("seat"))
    except (TypeError, ValueError):
        return
    if seat not in PLAYER_SEATS:
        return
    if not session.accepts_takeovers():
        socketio.emit(
            "error_message",
            {"message": "On ne change de joueur qu'entre deux donnes. Réessaie au prochain récapitulatif."},
            to=request.sid,
        )
        return
    if not room.request_takeover(seat, request.sid, name):
        socketio.emit("error_message", {"message": "Ce siège est déjà pris."}, to=request.sid)
        return
    room.touch()
    _emit_lobby_update(room)
    session.broadcast()


@socketio.on("set_bot")
def on_set_bot(data):
    """Le lobby choisit quel bot occupera un siège vide au démarrage."""
    room = rooms.get((data or {}).get("code"))
    if not room:
        return
    if room.game_session and not room.game_session.finished:
        return  # partie en cours : choix verrouillés
    try:
        seat_key = int((data or {}).get("seat"))
    except (TypeError, ValueError):
        return
    bot_id = ((data or {}).get("bot_id") or "").strip()
    if not is_valid_bot(bot_id):
        return
    if room.set_bot_choice(seat_key, bot_id):
        _emit_lobby_update(room)


@socketio.on("set_time_control")
def on_set_time_control(data):
    """Le lobby choisit l'échiquier de temps : temps par coup et temps total."""
    room = rooms.get((data or {}).get("code"))
    if not room:
        return
    # On rediffuse dans tous les cas : si la valeur est refusée (hors preset,
    # partie déjà lancée), le sélecteur du demandeur reprend l'échiquier réel.
    room.set_time_control((data or {}).get("move_time"), (data or {}).get("total_time"))
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
    # Choix de bots par siège envoyés par le lobby ({seat: bot_id}) ; le
    # serveur ne retient que les ids valides, sur des sièges encore vides.
    raw_bots = (data or {}).get("bots") or {}
    bot_ids = {}
    if isinstance(raw_bots, dict):
        for key, bid in raw_bots.items():
            try:
                seat = int(key)
            except (TypeError, ValueError):
                continue
            if seat in PLAYER_SEATS and isinstance(bid, str) and is_valid_bot(bid.strip()):
                bot_ids[seat] = bid.strip()

    if not fill_bots and not room.players_ready():
        socketio.emit(
            "error_message",
            {"message": "Il faut 4 joueurs aux 4 sièges (ou coche « compléter avec des bots »)."},
            to=request.sid,
        )
        return

    room.target_score = target_score
    room.touch()
    # Mémorise les choix dans la room pour cohérence (lobby + reconnexion).
    with room.lock:
        for seat, bid in bot_ids.items():
            if not room.seats[seat].occupied:
                room.bot_choices[seat] = bid
    session = GameSession(room, target_score=target_score, fill_bots=True, bot_ids=bot_ids)
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
    room.touch()
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
    room.touch()
    room.game_session.submit_card(seat, card_id)


@socketio.on("request_state")
def on_request_state(data):
    room = rooms.get((data or {}).get("code"))
    if not room:
        return
    if room.game_session:
        room.game_session.broadcast()
    else:
        socketio.emit("lobby_update", room.lobby_state(request.sid), to=request.sid)


@socketio.on("dismiss_recap")
def on_dismiss_recap(data):
    room = rooms.get((data or {}).get("code"))
    if not room or not room.game_session:
        return
    seat = room.seat_of_sid(request.sid)
    if seat is not None:
        room.game_session.dismiss_recap(seat)


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
        room.remove_spectator(request.sid)
    # Redémarre l'horloge d'inactivité : si c'était le dernier humain, le
    # salon commence alors son compte à rebours de fermeture.
    room.touch()
    _emit_lobby_update(room)


if __name__ == "__main__":
    # Local UI edits should appear on refresh without restarting an active game.
    # Production imports keep Flask's usual template caching.
    app.jinja_env.auto_reload = True
    port = int(os.environ.get("PORT", 5000))
    # Balayage périodique des salons abandonnés (fermeture automatique).
    socketio.start_background_task(_purge_loop)
    print("=" * 60)
    print("  Belote Coinchée — serveur local")
    print("=" * 60)
    print(f"  Sur cet ordinateur : http://localhost:{port}")
    print(f"  Depuis un téléphone sur le même Wi-Fi : http://{LAN_IP}:{port}")
    print("=" * 60)
    socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
