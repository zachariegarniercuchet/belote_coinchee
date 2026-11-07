"""Format JSON d'analyse : uniquement des donnes entièrement terminées."""

from dataclasses import asdict

from serialize import card_id


def donne_to_export(log, number, players, announcements, claim):
    contract = log.contract
    first_resolved = 8 - claim["remaining_tricks"] if claim else len(log.tricks)
    return {
        "number": number,
        "dealer": log.dealer,
        "first_player": (log.dealer + 1) % 4,
        "players": players,
        "cancelled": log.annulee,
        "initial_hands": {str(seat): [card_id(card) for card in hand]
                          for seat, hand in log.initial_hands.items()},
        "bidding_history": [
            {"seat": seat, "type": action.type.name, "points": action.points,
             "suit": action.suit.name if action.suit else None, "is_capot": action.is_capot}
            for seat, action in log.bidding_history
        ],
        "contract": {
            "player": contract.player, "team": contract.team, "points": contract.points,
            "suit": contract.suit.name, "is_capot": contract.is_capot,
            "coinche_state": contract.coinche_state.name,
            "coinche_by_team": contract.coinche_by_team,
        } if contract else None,
        "tricks": [
            {"number": index + 1, "leader": plays[0][0], "winner": winner,
             "points": sum(card.points(contract.suit) for _, card in plays),
             "resolved_by_claim": index >= first_resolved,
             "plays": [{"seat": seat, "card": card_id(card)} for seat, card in plays]}
            for index, (plays, winner) in enumerate(zip(log.tricks, log.trick_winners))
        ],
        "belote_announcements": [dict(entry) for entry in announcements],
        "claim": {"seat": log.claim.seat, "reason": log.claim.reason,
                  "from_trick": first_resolved + 1} if log.claim else None,
        "result": asdict(log.result) if log.result else None,
    }
