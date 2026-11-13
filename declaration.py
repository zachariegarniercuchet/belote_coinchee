"""Déclaration d'amour temporaire — à retirer avec son commit.

À la fin d'une partie jouée par exactement deux joueurs humains dont l'un
s'appelle « Zacharie », le serveur propose à Zacharie d'envoyer le contenu de
`declaration.txt` à sa partenaire. Le fichier est lu au moment de la réponse ;
le texte reste en attente tant que la partenaire ne l'a pas fermé, donc il lui
parvient aussi après une reconnexion.

Événements : `declaration_ask` (popup chez Zacharie), `declaration_reply`
(sa réponse), `declaration_sent` / `error_message` (retour), `declaration_show`
(plein écran chez la partenaire), `declaration_closed` (elle ferme).
"""

from __future__ import annotations

import os

from extensions import socketio
from rooms import PLAYER_SEATS

ZACHARIE = "zacharie"
DECLARATION_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "declaration.txt")


def _human_seats(room):
    """Sièges occupés par un humain : (siège, prénom, sid ou None)."""
    with room.lock:
        return [
            (seat, room.seats[seat].name, room.seats[seat].sid)
            for seat in PLAYER_SEATS
            if room.seats[seat].occupied
        ]


def _pair(room):
    """(Zacharie, partenaire) si la table réunit exactement deux humains dont Zacharie.

    Renvoie (None, None) sinon : pas de popup quand un siège de plus est
    humain, quand il en manque un, ou quand Zacharie n'est pas à la table.
    """
    humans = _human_seats(room)
    if len(humans) != 2:
        return None, None
    for entry in humans:
        if (entry[1] or "").strip().casefold() == ZACHARIE:
            other = next(h for h in humans if h[0] != entry[0])
            return entry, other
    return None, None


def read_declaration() -> str | None:
    """Contenu de `declaration.txt` (lu à l'envoi, jamais mis en cache)."""
    try:
        with open(DECLARATION_PATH, encoding="utf-8") as handle:
            text = handle.read().strip()
    except (OSError, UnicodeDecodeError):
        return None
    return text or None


def maybe_offer(session) -> None:
    """Propose l'envoi à Zacharie (fin de partie, ou retour de sa connexion)."""
    # Défensif : les tests branchent parfois un faux session minimal.
    room = getattr(session, "room", None)
    if room is None or not getattr(session, "finished", False):
        return
    zacharie, _partner = _pair(room)
    if zacharie is None:
        return
    with room.lock:
        decision = room.declaration_decision
    # Une décision déjà prise pour CETTE partie ne redemande rien ; une
    # décision d'une partie précédente ne bloque pas la suivante.
    if decision is not None and decision[0] == session.game_id:
        return
    _seat, _name, sid = zacharie
    if sid is None:
        return  # Zacharie hors ligne : relancé à sa reconnexion.
    socketio.emit("declaration_ask", {"code": room.code}, to=sid)


def record_reply(room, session, sid, accept: bool) -> None:
    """Traite la réponse de Zacharie et, le cas échéant, prépare l'envoi."""
    zacharie, partner = _pair(room)
    if zacharie is None or zacharie[2] != sid or partner is None:
        return
    with room.lock:
        if room.declaration_decision is not None and room.declaration_decision[0] == session.game_id:
            return  # déjà répondu pour cette partie
    if not accept:
        with room.lock:
            room.declaration_decision = (session.game_id, "skipped")
        return
    text = read_declaration()
    if not text:
        socketio.emit(
            "error_message",
            {"message": "declaration.txt est introuvable ou vide."},
            to=sid,
        )
        return  # aucune décision enregistrée : Zacharie pourra réessayer
    with room.lock:
        room.declaration_decision = (session.game_id, "sent")
        room.declaration_pending = text
    socketio.emit("declaration_sent", {"code": room.code}, to=sid)
    deliver_pending(room)


def deliver_pending(room) -> None:
    """Diffuse la déclaration en attente à la partenaire, si elle est connectée."""
    _zacharie, partner = _pair(room)
    with room.lock:
        text = room.declaration_pending
    if not text or partner is None or partner[2] is None:
        return
    socketio.emit("declaration_show", {"code": room.code, "text": text}, to=partner[2])


def acknowledge_close(room, sid) -> None:
    """La partenaire a fermé l'écran : il n'y a plus rien à livrer."""
    _zacharie, partner = _pair(room)
    if partner is None or partner[2] != sid:
        return
    with room.lock:
        room.declaration_pending = None
