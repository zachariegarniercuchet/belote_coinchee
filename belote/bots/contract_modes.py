"""Public-information card play for contracts without cutting (SA / TA).

Kept separate from every bot's historical suited-contract policy.
"""

from ..cards import Card, Rank
from ..trick import partner_of, team_of, trick_winner


def choose_mode_card(bot, hand, trick, legal):
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
