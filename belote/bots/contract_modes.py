"""Public-information card play for contracts without cutting (SA / TA).

Kept separate from every bot's historical suited-contract policy.
"""

from ..cards import Card, Rank, Suit, ContractMode, ATOUT_ORDER, NONATOUT_ORDER
from ..trick import partner_of, team_of, trick_winner


def qualified_purges(hand, mode, played=None):
    """Three cards with the top two, or four with the top remaining card."""
    order = ATOUT_ORDER if mode is ContractMode.TOUT_ATOUT else NONATOUT_ORDER
    played = played or {}
    suits = set()
    for suit in Suit:
        held = {c.rank for c in hand if c.suit == suit}
        remaining = [r for r in order if r not in played.get(suit, ())]
        if remaining and ((len(held) >= 4 and remaining[0] in held) or
                          (len(held) >= 3 and len(remaining) >= 2 and set(remaining[:2]) <= held)):
            suits.add(suit)
    return suits


def choose_mode_card(bot, hand, trick, legal, purge_suits=None):
    mode = trick.atout
    played = getattr(bot, "played_by_suit", {})
    known_voids = getattr(bot, "void_suits", {})

    def master(card):
        known = set(played.get(card.suit, ()))
        known.update(c.rank for _, c in trick.plays if c.suit == card.suit)
        known.update(c.rank for c in hand if c.suit == card.suit)
        return not any(rank not in known and Card(rank, card.suit).strength_index(mode)
                       < card.strength_index(mode) for rank in Rank)

    def safe(card):
        hypothetical = trick.plays + [(bot.player_id, card)]
        winner = trick_winner(hypothetical, mode)
        best = next(c for p, c in hypothetical if p == winner)
        # Include current-trick voids; no imaginary cutting threat in SA/TA.
        voids = {p: set(known_voids.get(p, ())) for p in range(4)}
        for p, c in trick.plays:
            if c.suit != trick.plays[0][1].suit:
                voids[p].add(trick.plays[0][1].suit)
        later = [(bot.player_id + n) % 4 for n in range(1, 4 - len(trick.plays))]
        return master(best) or all(team_of(p) == team_of(bot.player_id)
                                  or best.suit in voids[p] for p in later)

    def discard(pool):
        return min(pool, key=lambda c: (master(c), c.points(mode), -c.strength_index(mode)))

    if not trick.plays:
        if purge_suits is not None:
            # Brooklyn: retain short-suit masters; only cash them to purge
            # a supported long suit, or when no waste remains anywhere.
            purge_suits.update(qualified_purges(hand, mode, played))
            opponents = [p for p in range(4) if team_of(p) != team_of(bot.player_id)]
            partner = partner_of(bot.player_id)
            candidates = []
            for suit in Suit:
                cards = [c for c in legal if c.suit == suit]
                partner_only = (all(suit in known_voids.get(p, ()) for p in opponents)
                                and suit not in known_voids.get(partner, ()))
                if not cards or (suit not in purge_suits and not partner_only):
                    continue
                top = min(cards, key=lambda c: c.strength_index(mode))
                is_master = master(top)
                # No master: force the absent honours with a low card.
                pick = top if is_master else max(cards, key=lambda c: c.strength_index(mode))
                candidates.append((is_master, len(cards), pick.points(mode) if is_master else -pick.points(mode), pick))
            if candidates:
                return max(candidates, key=lambda item: item[:3])[-1]
            waste = [c for c in legal if not master(c)]
            if waste:
                return min(waste, key=lambda c: (-sum(h.suit == c.suit for h in hand),
                                                c.points(mode), -c.strength_index(mode)))
        masters = [c for c in legal if master(c)]
        if masters:
            return max(masters, key=lambda c: (c.points(mode), sum(h.suit == c.suit for h in hand)))
        # Establish a long suit without throwing its valuable honour under a master.
        return min(legal, key=lambda c: (-sum(h.suit == c.suit for h in hand),
                                        c.points(mode), -c.strength_index(mode)))

    partner = partner_of(bot.player_id)
    if trick_winner(trick.plays, mode) == partner:
        safe_feeds = [c for c in legal if trick_winner(trick.plays + [(bot.player_id, c)], mode) == partner
                      and safe(c)]
        losers = [c for c in safe_feeds if not master(c)]
        # Do not donate a master (notably a SA ace or TA jack) while waste remains.
        if losers:
            return max(losers, key=lambda c: (c.points(mode), sum(h.suit == c.suit for h in hand) == 1))
        if safe_feeds:
            return discard(safe_feeds)
    winning = [c for c in legal if trick_winner(trick.plays + [(bot.player_id, c)], mode) == bot.player_id]
    if winning:
        secure = [c for c in winning if safe(c)]
        if secure:
            return max(secure, key=lambda c: (c.points(mode), -c.strength_index(mode)))
        return max(winning, key=lambda c: c.strength_index(mode))
    return discard(legal)
