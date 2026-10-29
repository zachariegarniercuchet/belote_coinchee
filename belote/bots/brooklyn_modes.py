"""Brooklyn SA/TA bidding: recoverable cards, controls and public support.

Initial rule-based estimates, not calibrated probabilities. No cutting/void
credit, no imaginary trump suit and no transfer of another contract's credits.
"""

from ..bidding import ActionType
from ..cards import ATOUT_ORDER, NONATOUT_ORDER, ContractMode, Rank, Suit
from ..trick import partner_of, team_of


def mode_value(hand, mode):
    order = ATOUT_ORDER if mode is ContractMode.TOUT_ATOUT else NONATOUT_ORDER
    value, controls, pairs = 0.0, 0, 0
    for suit in Suit:
        held = {c.rank: c for c in hand if c.suit == suit}
        survivors = dict(held)
        prefix = []
        for rank in order:
            if rank not in held:
                break
            prefix.append(rank)
        controls += len(prefix)
        # Establishment sacrifices low cards to the absent higher honours.
        for rank in order:
            if rank not in held:
                weaker = [r for r in survivors if order.index(r) > order.index(rank)]
                if weaker:
                    survivors.pop(max(weaker, key=order.index))
        value += sum(c.points(mode) * (.85 if c.rank in prefix else .55)
                     for c in survivors.values())
        if mode is ContractMode.TOUT_ATOUT and {Rank.ROI, Rank.DAME} <= held.keys():
            pairs += 1
    return round(value + pairs * 20, 2), controls


def mode_opening(hand, mode):
    value, controls = mode_value(hand, mode)
    # Belotes alone must not finance a bid without plausible tricks.
    if controls < 2 or value < 30:
        return 0
    return min(160 if mode is ContractMode.SANS_ATOUT else 240,
               80 + 10 * int((value - 30) // 10))


def mode_support(hand, mode):
    order = ATOUT_ORDER if mode is ContractMode.TOUT_ATOUT else NONATOUT_ORDER
    credits = 0
    for suit in Suit:
        held = {c.rank for c in hand if c.suit == suit}
        # Only contiguous winners from A in SA / J in TA. A TA ace without
        # its J/9 is not an immediate master and must not get an ace bonus.
        for rank in order:
            if rank not in held:
                break
            credits += 10
        if mode is ContractMode.TOUT_ATOUT and {Rank.ROI, Rank.DAME} <= held:
            credits += 20
    return credits


def choose_mode_bid(bot, hand, state, legal, suited_action):
    # No speculative coinche based on an evaluator for a single trump suit.
    if (state.contract and isinstance(state.contract.suit, ContractMode)
            and suited_action.type in (ActionType.COINCHE, ActionType.SURCOINCHE)):
        suited_action = next(a for a in legal if a.type is ActionType.PASSE)
    if suited_action.type in (ActionType.COINCHE, ActionType.SURCOINCHE):
        return suited_action

    episode = []
    for seat, action in state.history:
        if team_of(seat) != team_of(bot.player_id) or action.type is not ActionType.ENCHERE:
            continue
        if episode and episode[-1][1].suit != action.suit:
            episode = []
        episode.append((seat, action))
    choices = []
    certain_capots = [a for a in legal if a.type is ActionType.ENCHERE
                      and isinstance(a.suit, ContractMode) and a.is_capot
                      and len(hand) == 8 and mode_value(hand, a.suit)[1] == 8]
    if certain_capots:
        if suited_action.type is ActionType.ENCHERE and suited_action.is_capot:
            return suited_action
        # A guaranteed TA capot can additionally retain its belotes.
        return max(certain_capots, key=lambda a: a.suit is ContractMode.TOUT_ATOUT)
    for mode in ContractMode:
        ceiling = mode_opening(hand, mode)
        supporting = bool(episode and episode[-1][1].suit is mode)
        if supporting:
            latest = episode[-1][1]
            if latest.is_capot:
                continue
            spent = {bot.player_id: 0, partner_of(bot.player_id): 0}
            for (_, before), (seat, action) in zip(episode, episode[1:]):
                if before.points is not None and action.points is not None:
                    spent[seat] += action.points - before.points
            if episode[0][0] == bot.player_id:
                ceiling += spent[partner_of(bot.player_id)]
            else:
                ceiling = latest.points + max(0, mode_support(hand, mode) - spent[bot.player_id])
        candidates = [a for a in legal if a.type is ActionType.ENCHERE and a.suit is mode
                      and not a.is_capot and a.points <= ceiling]
        if candidates:
            choices.append((max(candidates, key=lambda a: a.points), supporting))
    if not choices:
        return suited_action
    action, _ = max(choices, key=lambda item: (item[0].points, item[1]))
    # Keep the historical choice on equal value; a mode must justify a higher
    # independent bid to replace it. Opponent overcalls do not create credit.
    if suited_action.type is ActionType.ENCHERE and suited_action.comparison_value() >= action.points:
        return suited_action
    return action
