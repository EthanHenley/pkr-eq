"""Generate preflop_equity.json with equity for all 169 hand categories x 1-8 opponents."""

import json
import random
from itertools import combinations
from treys import Card, Deck, Evaluator

RANKS = "AKQJT98765432"
evaluator = Evaluator()
NUM_SIMULATIONS = 5000  # per hand category per opponent count


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


def simulate_equity(hole, num_opponents, num_sims=NUM_SIMULATIONS):
    """Monte Carlo equity vs num_opponents random opponents + random board.

    Hero wins only if they beat ALL opponents.
    """
    full_deck = Deck.GetFullDeck()
    remaining = [c for c in full_deck if c not in hole]

    wins = 0
    ties = 0
    total = 0

    cards_needed = 5 + 2 * num_opponents  # board + all opponent hands

    for _ in range(num_sims):
        drawn = random.sample(remaining, cards_needed)
        board = drawn[:5]
        hero_score = evaluator.evaluate(board, hole)

        best_opp_score = None
        for o in range(num_opponents):
            opp = drawn[5 + o * 2: 7 + o * 2]
            opp_score = evaluator.evaluate(board, opp)
            if best_opp_score is None or opp_score < best_opp_score:
                best_opp_score = opp_score

        if hero_score < best_opp_score:
            wins += 1
        elif hero_score == best_opp_score:
            ties += 1
        total += 1

    return (wins + ties / 2) / total


def main():
    categories = list(hand_categories())
    opponent_counts = list(range(1, 9))  # 1 through 8
    total_sims = len(categories) * len(opponent_counts)

    print(f"Computing equity for {len(categories)} hand categories x "
          f"{len(opponent_counts)} opponent counts "
          f"({NUM_SIMULATIONS} sims each, {total_sims} total)...")

    results = {}
    done = 0

    for num_opp in opponent_counts:
        opp_results = {}
        for key in categories:
            hole = representative_cards(key)
            eq = simulate_equity(hole, num_opp)
            opp_results[key] = round(eq, 4)
            done += 1
            if done % (len(categories) // 4) == 0 or done == total_sims:
                print(f"  {done}/{total_sims}  {num_opp}opp  {key} = {opp_results[key]:.4f}")
        results[str(num_opp)] = opp_results
        print(f"  -- Finished {num_opp} opponent(s) --")

    with open("preflop_equity.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote preflop_equity.json ({len(opponent_counts)} tables x {len(categories)} entries)")


if __name__ == "__main__":
    main()
