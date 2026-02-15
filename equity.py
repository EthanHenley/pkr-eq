import json
import os
from itertools import combinations
from treys import Card, Evaluator

_evaluator = Evaluator()

_PREFLOP_EQUITY_FILE = os.path.join(os.path.dirname(__file__), "preflop_equity.json")
if os.path.exists(_PREFLOP_EQUITY_FILE):
    with open(_PREFLOP_EQUITY_FILE) as _f:
        _PREFLOP_EQUITY = json.load(_f)
else:
    _PREFLOP_EQUITY = {}

_RANK_ORDER = "AKQJT98765432"


def _hand_key(hole_cards):
    """Convert two treys card ints to canonical notation (e.g. 'AKs', 'TT', '97o')."""
    s1 = Card.int_to_str(hole_cards[0])
    s2 = Card.int_to_str(hole_cards[1])
    r1, suit1 = s1[0], s1[1]
    r2, suit2 = s2[0], s2[1]
    # Ensure higher rank comes first
    if _RANK_ORDER.index(r1) > _RANK_ORDER.index(r2):
        r1, r2 = r2, r1
        suit1, suit2 = suit2, suit1
    if r1 == r2:
        return f"{r1}{r2}"
    elif suit1 == suit2:
        return f"{r1}{r2}s"
    else:
        return f"{r1}{r2}o"


def calculate_equity(hole_cards, community_cards, num_opponents, remaining_cards):
    """Calculate win equity via enumeration.

    For preflop with many opponents this can be slow. We sample when the
    enumeration space is too large.
    """
    if not community_cards and _PREFLOP_EQUITY:
        key = _hand_key(hole_cards)
        if key in _PREFLOP_EQUITY:
            return _PREFLOP_EQUITY[key]

    board_needed = 5 - len(community_cards)
    remaining = list(remaining_cards)

    if board_needed == 0:
        return _equity_fixed_board(hole_cards, community_cards, num_opponents, remaining)

    # Estimate enumeration size
    from math import comb
    board_combos = comb(len(remaining), board_needed)
    # If too many combos, sample
    if board_combos > 500:
        return _equity_sampled(hole_cards, community_cards, num_opponents, remaining, board_needed, sample_size=300)

    wins = 0
    ties = 0
    total = 0

    for board_draw in combinations(remaining, board_needed):
        full_board = community_cards + list(board_draw)
        deck_after_board = [c for c in remaining if c not in board_draw]
        w, t, n = _eval_against_opponents(hole_cards, full_board, num_opponents, deck_after_board)
        wins += w
        ties += t
        total += n

    if total == 0:
        return 0.5
    return (wins + ties / 2) / total


def _equity_sampled(hole_cards, community_cards, num_opponents, remaining, board_needed, sample_size=300):
    import random
    wins = 0
    ties = 0
    total = 0

    for _ in range(sample_size):
        board_draw = random.sample(remaining, board_needed)
        full_board = community_cards + board_draw
        deck_after_board = [c for c in remaining if c not in board_draw]
        w, t, n = _eval_against_opponents(hole_cards, full_board, num_opponents, deck_after_board)
        wins += w
        ties += t
        total += n

    if total == 0:
        return 0.5
    return (wins + ties / 2) / total


def _equity_fixed_board(hole_cards, board, num_opponents, remaining):
    wins = 0
    ties = 0
    total = 0
    w, t, n = _eval_against_opponents(hole_cards, board, num_opponents, remaining)
    wins += w
    ties += t
    total += n
    if total == 0:
        return 0.5
    return (wins + ties / 2) / total


def _eval_against_opponents(hole_cards, board, num_opponents, deck):
    """Enumerate opponent hands and count wins/ties.

    For speed, we limit opponent combos and assume independent single-opponent
    matchups (1v1 equity approximation for multi-way — good enough for display).
    """
    hero_score = _evaluator.evaluate(board, hole_cards)

    wins = 0
    ties = 0
    total = 0

    opponent_combos = list(combinations(deck, 2))
    # Cap opponent combos for performance
    if len(opponent_combos) > 500:
        import random
        opponent_combos = random.sample(opponent_combos, 500)

    for opp_hand in opponent_combos:
        opp_score = _evaluator.evaluate(board, list(opp_hand))
        total += 1
        if hero_score < opp_score:  # lower is better in treys
            wins += 1
        elif hero_score == opp_score:
            ties += 1

    return wins, ties, total
