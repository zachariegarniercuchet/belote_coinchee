"""
Fait le pont entre le moteur `belote` (synchrone, pensé pour la console) et
des joueurs humains connectés en réseau (qui répondent de façon asynchrone,
au rythme d'un tap sur un téléphone).

Principe : chaque salon avec une partie en cours possède un thread dédié
(GameSession.run, lancé via socketio.start_background_task) qui rejoue very
exactement la logique de `belote.game.Donne.play()` / `Game.play_one_donne()`,
mais instrumentée pour diffuser l'état à chaque étape et pour bloquer (via un
threading.Event) quand c'est au tour d'un joueur humain, jusqu'à ce que sa
réponse arrive par Socket.IO depuis son téléphone.

On ne modifie aucun fichier du package `belote/` : on le réutilise tel quel.
"""

from __future__ import annotations

import random
import threading
import time

from belote.bidding import BiddingState
from belote.bots import HeuristicBot
from belote.cards import cut_deck, deal, new_shuffled_deck
from belote.game import DonneLog, Game
from belote.player import Player
from belote.scoring import compute_donne_score, find_belote_holder
from belote.trick import TrickState, team_of

from extensions import socketio
from rooms import PLAYER_SEATS
from serialize import bid_action_to_dict, card_from_id, card_id, card_to_dict, sorted_hand

TRICK_COLLECT_PAUSE_RANGE = (1.6, 2.3)   # secondes pour "voir" le pli complet avant qu'il ne soit ramassé
BOT_BID_THINK_RANGE = (0.9, 1.9)     # secondes de "réflexion" simulée d'un bot avant d'enchérir
BOT_CARD_THINK_RANGE = (0.8, 1.7)    # secondes de "réflexion" simulée d'un bot avant de jouer une carte


class GameContext:
    """Instantané mutable de l'état de jeu, relu à chaque diffusion (broadcast)."""

    def __init__(self):
        self.phase = "lobby"           # lobby | bidding | trick | donne_annulee | donne_end | game_end | error
        self.dealer = None
        self.donne_number = 0
        self.hands = {p: [] for p in PLAYER_SEATS}
        self.bidding_state: BiddingState | None = None
        self.current_trick: TrickState | None = None
        self.completed_trick_cards = None   # liste (seat, card) du dernier pli, affichée brièvement
        self.last_trick_winner_seat = None
        self.last_completed_trick = None        # persiste jusqu'au pli suivant (pour la pile cliquable)
        self.last_completed_trick_winner_seat = None
        self.tricks_won_this_donne = {0: 0, 1: 0}
        self.last_donne_result = None
        self.waiting_seat = None
        self.waiting_kind = None       # "bid" | "card" | None
        self.pending_legal_bid = None
        self.pending_legal_cards = None
        self.error_message = None


class NetworkPlayer(Player):
    """Un joueur humain : choose_bid/choose_card bloquent jusqu'à réception d'un choix
    envoyé depuis le téléphone via Socket.IO (voir GameSession.submit_bid/submit_card)."""

    def __init__(self, seat: int, session: "GameSession", name: str):
        super().__init__(seat, name)
        self.session = session

    def choose_bid(self, hand, bidding_state, legal_actions):
        return self.session._wait_for_choice(self.player_id, "bid")

    def choose_card(self, hand, trick_state, legal_cards):
        return self.session._wait_for_choice(self.player_id, "card")

    def notify(self, message: str) -> None:
        pass


class NetworkGame(Game):
    """Reprend Game/Donne du moteur, mais diffuse l'état à chaque étape atomique."""

    def __init__(self, players, target_score, session: "GameSession", rng=None, first_dealer=None):
        super().__init__(players, target_score=target_score, rng=rng, first_dealer=first_dealer)
        self.session = session

    def play_one_donne(self) -> DonneLog:
        if self.finished:
            raise ValueError("La partie est déjà terminée.")
        log = self._play_network_donne(self.dealer)
        self.donne_logs.append(log)
        if not log.annulee:
            for team, pts in log.result.final_scores.items():
                self.cumulative_scores[team] += pts
            self._check_end_conditions(log.result)
        if log.result is not None:
            self.session.prepare_recap()
        self.session.broadcast()
        self.dealer = (self.dealer - 1) % 4
        return log

    def _play_network_donne(self, dealer: int) -> DonneLog:
        ctx = self.session.ctx
        rng = self.rng

        deck = cut_deck(new_shuffled_deck(rng), rng)
        starting_player = (dealer - 1) % 4
        hands = deal(deck, starting_player)
        initial_hands = {p: list(h) for p, h in hands.items()}

        ctx.dealer = dealer
        ctx.donne_number = len(self.donne_logs) + 1
        ctx.hands = {p: list(h) for p, h in hands.items()}
        ctx.phase = "bidding"
        ctx.current_trick = None
        ctx.completed_trick_cards = None
        ctx.last_completed_trick = None
        ctx.last_completed_trick_winner_seat = None
        ctx.last_donne_result = None
        ctx.tricks_won_this_donne = {0: 0, 1: 0}

        bidding_state = BiddingState(dealer=dealer)
        ctx.bidding_state = bidding_state
        self.session.broadcast()

        while not bidding_state.finished:
            p = bidding_state.current_player
            legal = bidding_state.legal_actions()
            ctx.waiting_seat = p
            ctx.waiting_kind = "bid"
            ctx.pending_legal_bid = legal
            self.session.broadcast()

            if not isinstance(self.players[p], NetworkPlayer):
                self.session.sleep(random.uniform(*BOT_BID_THINK_RANGE))

            action = self.players[p].choose_bid(hands[p], bidding_state, legal)
            bidding_state.apply(action)

            ctx.waiting_seat = None
            ctx.waiting_kind = None
            ctx.pending_legal_bid = None
            self.session.broadcast()

        log = DonneLog(
            dealer=dealer,
            initial_hands=initial_hands,
            bidding_history=bidding_state.history,
            contract=bidding_state.contract,
            annulee=bidding_state.annulee,
        )

        if bidding_state.annulee:
            ctx.phase = "donne_annulee"
            self.session.broadcast()
            return log

        contract = bidding_state.contract
        atout = contract.suit
        leader = (dealer - 1) % 4
        trick_points = {0: 0, 1: 0}
        tricks_won_by_team = {0: 0, 1: 0}
        last_trick_winner = leader

        ctx.phase = "trick"

        for _ in range(8):
            trick = TrickState(leader=leader, atout=atout)
            ctx.current_trick = trick
            ctx.completed_trick_cards = None
            self.session.broadcast()

            for _ in range(4):
                p = trick.current_player
                legal = trick.legal_cards_for(hands[p])
                ctx.waiting_seat = p
                ctx.waiting_kind = "card"
                ctx.pending_legal_cards = legal
                self.session.broadcast()

                if not isinstance(self.players[p], NetworkPlayer):
                    self.session.sleep(random.uniform(*BOT_CARD_THINK_RANGE))

                card = self.players[p].choose_card(hands[p], trick, legal)
                if card not in legal:
                    raise ValueError(f"Le joueur {p} a tenté de jouer une carte illégale: {card}")
                trick.play(p, card)
                hands[p].remove(card)
                ctx.hands[p] = list(hands[p])

                ctx.waiting_seat = None
                ctx.waiting_kind = None
                ctx.pending_legal_cards = None
                self.session.broadcast()

            winner = trick.winner()
            last_trick_winner = winner
            trick_points[team_of(winner)] += trick.points()
            tricks_won_by_team[team_of(winner)] += 1
            ctx.tricks_won_this_donne = dict(tricks_won_by_team)

            log.tricks.append(list(trick.plays))
            log.trick_winners.append(winner)

            ctx.completed_trick_cards = list(trick.plays)
            ctx.last_trick_winner_seat = winner
            ctx.last_completed_trick = list(trick.plays)
            ctx.last_completed_trick_winner_seat = winner
            ctx.current_trick = None
            self.session.broadcast()
            self.session.sleep(random.uniform(*TRICK_COLLECT_PAUSE_RANGE))

            leader = winner

        capot_team = 0 if tricks_won_by_team[0] == 8 else (1 if tricks_won_by_team[1] == 8 else None)
        belote_holder = find_belote_holder(initial_hands, atout)
        belote_team = team_of(belote_holder) if belote_holder is not None else None

        result = compute_donne_score(
            contract=contract,
            trick_points=trick_points,
            last_trick_winner=last_trick_winner,
            capot_team=capot_team,
            belote_team=belote_team,
        )
        log.result = result

        ctx.last_donne_result = result
        ctx.phase = "donne_end"
        ctx.hands = {p: [] for p in PLAYER_SEATS}
        return log


class GameSession:
    """Pilote une NetworkGame pour un salon donné, et diffuse l'état à tous les sockets connectés."""

    def __init__(self, room, target_score: int, fill_bots: bool = True):
        self.room = room
        self.ctx = GameContext()
        self.finished = False
        self.winner_team = None
        self._stop = False
        self._lock = threading.Lock()
        self._pending_event: threading.Event | None = None
        self._pending_seat = None
        self._pending_kind = None
        self._pending_choice = None
        self._recap_closed = threading.Event()
        self._recap_pending_seats = set()

        players = {}
        bot_names = {
            0: "Théo Bot",
            1: "Anna Bot",
            2: "Jade Bot",
            3: "Gabin Bot",
        }
        for p in PLAYER_SEATS:
            seat = room.seats[p]
            if seat.occupied:
                players[p] = NetworkPlayer(p, self, seat.name)
            elif fill_bots:
                players[p] = HeuristicBot(p, name=bot_names[p])
            else:
                raise ValueError("Sièges incomplets et remplissage par bots désactivé.")
        self.players = players
        self.game = NetworkGame(players, target_score=target_score, session=self)

    # --- cycle de vie -----------------------------------------------------

    def run(self):
        try:
            while not self.game.finished and not self._stop:
                log = self.game.play_one_donne()
                if self.game.finished or self._stop:
                    break
                if log.result is not None:
                    self._wait_for_recap()
                    self._recap_closed.clear()
        except Exception as exc:  # ne doit jamais planter le thread silencieusement
            self.ctx.phase = "error"
            self.ctx.error_message = str(exc)
            self.broadcast()
            raise
        finally:
            self.finished = self.game.finished
            self.winner_team = self.game.winner_team
            if self.finished:
                self.ctx.phase = "game_end"
                self.broadcast()

    def stop(self):
        self._stop = True
        self._recap_closed.set()

    def _wait_for_recap(self):
        with self._lock:
            pending = bool(self._recap_pending_seats)
        if not pending:
            return
        self._recap_closed.wait()
        with self._lock:
            self._recap_pending_seats.clear()

    def prepare_recap(self):
        with self.room.lock:
            board = self.room.seats.get("board")
            if board and board.occupied:
                pending = {"board"}
            else:
                pending = {
                    seat for seat in PLAYER_SEATS if self.room.seats[seat].occupied
                }
        with self._lock:
            self._recap_pending_seats = pending
            if not pending:
                self._recap_closed.set()

    def dismiss_recap(self, seat):
        with self._lock:
            if seat not in self._recap_pending_seats:
                return
            self._recap_pending_seats.remove(seat)
            if not self._recap_pending_seats:
                self._recap_closed.set()

    def sleep(self, seconds: float):
        end = time.time() + seconds
        while time.time() < end and not self._stop:
            time.sleep(0.2)

    # --- réception des choix humains --------------------------------------

    def _wait_for_choice(self, seat: int, kind: str):
        event = threading.Event()
        with self._lock:
            self._pending_event = event
            self._pending_seat = seat
            self._pending_kind = kind
            self._pending_choice = None
        event.wait()
        with self._lock:
            return self._pending_choice

    def submit_bid(self, seat: int, index: int) -> bool:
        with self._lock:
            if self._pending_seat != seat or self._pending_kind != "bid" or self._pending_event is None:
                return False
            legal = self.ctx.pending_legal_bid or []
            if not (0 <= index < len(legal)):
                return False
            self._pending_choice = legal[index]
            ev = self._pending_event
            self._pending_event = None
        ev.set()
        return True

    def submit_card(self, seat: int, card_id: str) -> bool:
        with self._lock:
            if self._pending_seat != seat or self._pending_kind != "card" or self._pending_event is None:
                return False
            legal = self.ctx.pending_legal_cards or []
            card = card_from_id(card_id, legal)
            if card is None:
                return False
            self._pending_choice = card
            ev = self._pending_event
            self._pending_event = None
        ev.set()
        return True

    # --- diffusion de l'état -----------------------------------------------

    def _contract_dict(self):
        bs = self.ctx.bidding_state
        contract = bs.contract if bs else None
        if not contract:
            return None
        return {
            "player": contract.player,
            "team": contract.team,
            "points": contract.points,
            "suit": contract.suit.name,
            "symbol": contract.suit.symbol(),
            "is_capot": contract.is_capot,
            "coinche_state": contract.coinche_state.name,
        }

    def _bidding_history(self):
        bs = self.ctx.bidding_state
        if not bs:
            return []
        return [
            {
                "seat": p,
                "label": repr(a),
                "type": a.type.name,
                "suit": a.suit.name if a.suit else None,
            }
            for p, a in bs.history
        ]

    def _trick_plays_dict(self, plays):
        if not plays:
            return []
        return [{"seat": p, "card": card_to_dict(c)} for p, c in plays]

    def _result_dict(self):
        r = self.ctx.last_donne_result
        if r is None:
            return None
        return {
            "preneur_team": r.preneur_team,
            "defense_team": r.defense_team,
            "contract_reached": r.contract_reached,
            "final_scores": {"0": r.final_scores.get(0, 0), "1": r.final_scores.get(1, 0)},
            "raw_points": {"0": r.raw_points.get(0, 0), "1": r.raw_points.get(1, 0)},
            "capot_team": r.capot_team,
            "belote_team": r.belote_team,
            "dix_de_der_team": r.dix_de_der_team,
        }

    def _build_common(self):
        ctx = self.ctx
        board_seat = self.room.seats.get("board")
        return {
            "code": self.room.code,
            "phase": ctx.phase,
            "error_message": ctx.error_message,
            "dealer": ctx.dealer,
            "donne_number": ctx.donne_number,
            "target_score": self.game.target_score,
            "cumulative_scores": {
                "0": self.game.cumulative_scores.get(0, 0),
                "1": self.game.cumulative_scores.get(1, 0),
            },
            "seats_names": {
                str(k): (
                    self.players[k].name if k in self.players
                    else self.room.seats[k].name
                ) for k in (0, 1, 2, 3)
            },
            "board_present": bool(board_seat and board_seat.occupied),
            "waiting_seat": ctx.waiting_seat,
            "waiting_kind": ctx.waiting_kind,
            "waiting_seat_name": (
                self.room.seats[ctx.waiting_seat].name if ctx.waiting_seat is not None else None
            ),
            "contract": self._contract_dict(),
            "bidding_history": self._bidding_history(),
            "current_trick": self._trick_plays_dict(ctx.current_trick.plays if ctx.current_trick else []),
            "completed_trick": self._trick_plays_dict(ctx.completed_trick_cards),
            "last_trick_winner_seat": ctx.last_trick_winner_seat,
            "last_completed_trick": self._trick_plays_dict(ctx.last_completed_trick),
            "last_completed_trick_winner_seat": ctx.last_completed_trick_winner_seat,
            "hand_counts": {str(p): len(ctx.hands.get(p, [])) for p in PLAYER_SEATS},
            "tricks_won_this_donne": {
                "0": ctx.tricks_won_this_donne.get(0, 0),
                "1": ctx.tricks_won_this_donne.get(1, 0),
            },
            "last_donne_result": self._result_dict(),
            "score_history": [
                {
                    "0": log.result.final_scores.get(0, 0),
                    "1": log.result.final_scores.get(1, 0),
                }
                for log in self.game.donne_logs
                if log.result is not None
            ],
            "game_over": self.finished,
            "winner_team": self.winner_team,
        }

    def _build_for_player(self, common: dict, seat: int) -> dict:
        payload = dict(common)
        ctx = self.ctx
        your_turn = ctx.waiting_seat == seat
        payload.update({
            "your_seat": seat,
            "your_hand": [card_to_dict(c) for c in sorted_hand(ctx.hands.get(seat, []))],
            "your_turn": your_turn,
            "legal_bid_actions": (
                [bid_action_to_dict(a, i) for i, a in enumerate(ctx.pending_legal_bid)]
                if your_turn and ctx.waiting_kind == "bid" and ctx.pending_legal_bid else []
            ),
            "legal_card_ids": (
                [card_id(c) for c in ctx.pending_legal_cards]
                if your_turn and ctx.waiting_kind == "card" and ctx.pending_legal_cards else []
            ),
        })
        return payload

    def broadcast(self):
        common = self._build_common()
        with self.room.lock:
            seats_snapshot = {k: (v.sid, v.name) for k, v in self.room.seats.items()}

        for seat in PLAYER_SEATS:
            sid, _name = seats_snapshot[seat]
            if sid:
                socketio.emit("state_update", self._build_for_player(common, seat), to=sid)

        board_sid, _ = seats_snapshot["board"]
        if board_sid:
            payload = dict(common)
            payload.update({
                "your_seat": "board", "your_hand": [], "your_turn": False,
                "legal_bid_actions": [], "legal_card_ids": [],
            })
            socketio.emit("state_update", payload, to=board_sid)