"""Generate preflop_equity.json with 1v1 equity for all 169 hand categories."""

import json
import random
from itertools import combinations
from treys import Card, Deck, Evaluator

RANKS = "AKQJT98765432"
evaluator = Evaluator()
NUM_SIMULATIONS = 10000


def hand_categories():
    """Yield all 169 canonical hand notations: pairs, suited, offsuit."""
    for i, r1 in enumerate(RANKS):
        for j, r2 in enumerate(RANKS):
            if i < j:
                yield f"{r1}{r2}s"
            elif i > j:
                yield f"{r2}{r1}o"
            else:
                yield f"{r1}{r2}"


def representative_cards(hand_key):
    """Pick a concrete two-card combo for a hand category."""
    if len(hand_key) == 2:
        # Pair — pick two different suits
        r = hand_key[0]
        return [Card.new(f"{r}s"), Card.new(f"{r}h")]
    r1, r2, kind = hand_key[0], hand_key[1], hand_key[2]
    if kind == "s":
        return [Card.new(f"{r1}s"), Card.new(f"{r2}s")]
    else:
        return [Card.new(f"{r1}s"), Card.new(f"{r2}h")]


def simulate_equity(hole, num_sims=NUM_SIMULATIONS):
    """Monte Carlo 1v1 equity: random opponent + random board."""
    full_deck = Deck.GetFullDeck()
    remaining = [c for c in full_deck if c not in hole]

    wins = 0
    ties = 0
    total = 0

    for _ in range(num_sims):
        drawn = random.sample(remaining, 7)  # 5 board + 2 opponent
        board = drawn[:5]
        opp = drawn[5:7]

        hero_score = evaluator.evaluate(board, hole)
        opp_score = evaluator.evaluate(board, opp)

        if hero_score < opp_score:
            wins += 1
        elif hero_score == opp_score:
            ties += 1
        total += 1

    return (wins + ties / 2) / total


def main():
    results = {}
    categories = list(hand_categories())
    print(f"Computing equity for {len(categories)} hand categories "
          f"({NUM_SIMULATIONS} sims each)...")

    for i, key in enumerate(categories, 1):
        hole = representative_cards(key)
        eq = simulate_equity(hole)
        results[key] = round(eq, 4)
        if i % 13 == 0 or i == len(categories):
            print(f"  {i}/{len(categories)}  {key} = {results[key]:.4f}")

    with open("preflop_equity.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote preflop_equity.json ({len(results)} entries)")


if __name__ == "__main__":
    main()
