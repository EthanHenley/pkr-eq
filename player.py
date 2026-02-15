import random

# Self-preservation: AI avoids risking chips below this many big blinds
SELF_PRESERVE_BB = 5
# Probability that self-preservation kicks in when triggered
SELF_PRESERVE_CHANCE = 0.50


class Player:
    def __init__(self, name, chips=1000):
        self.name = name
        self.chips = chips
        self.hole_cards = []
        self.is_active = True       # still in tournament
        self.is_in_hand = False      # participating in current hand
        self.is_all_in = False
        self.current_bet = 0         # amount put in pot this round
        self.last_action = ""

    def bet(self, amount):
        amount = min(amount, self.chips)
        self.chips -= amount
        self.current_bet += amount
        if self.chips == 0:
            self.is_all_in = True
        return amount

    def fold(self):
        self.is_in_hand = False
        self.last_action = "fold"

    def reset_for_hand(self):
        self.hole_cards = []
        self.is_in_hand = self.is_active
        self.is_all_in = False
        self.current_bet = 0
        self.last_action = ""

    def reset_for_round(self):
        self.current_bet = 0

    def __repr__(self):
        return f"{self.name} (${self.chips})"


def _compute_action(equity, to_call, pot, chips, min_raise, max_raise, num_community=5):
    """Core pot-odds decision tree. Returns (action, amount)."""
    # Street-aware thresholds: preflop uses tighter ranges
    if num_community == 0:
        check_thresh = 0.45
        strong_thresh = 0.7
        fold_mult = 0.9
    else:
        check_thresh = 0.35
        strong_thresh = 0.6
        fold_mult = 0.8

    # Cap raise ceiling at 1.5x pot
    raise_cap = min(max_raise, pot + to_call + int(pot * 1.5))

    if to_call == 0:
        if equity < check_thresh:
            return ("check", 0)
        elif equity < strong_thresh:
            target = max(min_raise, int(pot * 0.5))
            target = min(target, raise_cap)
            if min_raise > max_raise:
                return ("check", 0)
            if target >= chips:
                return ("all-in", chips)
            return ("raise", target)
        else:
            fraction = 0.5 + (equity - strong_thresh) / (1.0 - strong_thresh) * 0.5
            target = max(min_raise, int(pot * fraction))
            target = min(target, raise_cap)
            if min_raise > max_raise:
                return ("check", 0)
            if target >= chips:
                return ("all-in", chips)
            return ("raise", target)
    else:
        pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0.5
        if to_call >= chips:
            # Require both pot odds AND a minimum equity floor to call off stack
            allin_floor = 0.5 if num_community == 0 else 0.4
            if equity >= pot_odds and equity >= allin_floor:
                return ("all-in", chips)
            else:
                return ("fold", 0)
        if equity < pot_odds * fold_mult:
            return ("fold", 0)
        elif equity < strong_thresh:
            return ("call", min(to_call, chips))
        else:
            if min_raise > max_raise:
                return ("call", min(to_call, chips))
            frac = (equity - strong_thresh) / (1.0 - strong_thresh)
            raise_to = int(min_raise + (raise_cap - min_raise) * frac)
            raise_to = max(min_raise, min(raise_to, raise_cap))
            if raise_to >= chips:
                return ("all-in", chips)
            return ("raise", raise_to)


def recommend_action(equity, to_call, pot, chips, min_raise, max_raise, num_community=5):
    """Return a short recommendation string based on equity and pot odds."""
    if equity is None:
        return None
    action, amount = _compute_action(equity, to_call, pot, chips, min_raise, max_raise, num_community)
    if action == "fold":
        return "Fold"
    if action == "check":
        return "Check"
    if action == "call":
        return f"Call ${amount}"
    if action == "all-in":
        return f"All-in ${amount}"
    # action == "raise"
    if to_call == 0:
        return f"Bet ${amount}"
    return f"Raise ${amount}"


class HumanPlayer(Player):
    def choose_action(self, to_call, min_raise, max_raise, pot, current_bet=0, equity=None, num_community=5, players_in_hand=2, big_blind=10):
        while True:
            if to_call == 0 and current_bet > 0:
                # BB option: can check or raise, no fold
                prompt = "[c]heck, [r]aise amount, [a]ll-in: "
            elif to_call == 0:
                prompt = "[c]heck, [b]et amount, [a]ll-in: "
            else:
                prompt = f"[c]all ${to_call}, [r]aise amount, [f]old, [a]ll-in: "
            action = input(prompt).strip().lower()

            if action == "f":
                if to_call == 0:
                    print("You can check for free.")
                    continue
                return "fold", 0
            elif action == "c":
                return ("call", min(to_call, self.chips)) if to_call > 0 else ("check", 0)
            elif action == "a":
                return "all-in", self.chips
            elif action.startswith("b") or action.startswith("r"):
                parts = action.split()
                if len(parts) == 2:
                    try:
                        amount = int(parts[1])
                    except ValueError:
                        print("Invalid amount.")
                        continue
                else:
                    try:
                        amount = int(input("Amount: ").strip())
                    except ValueError:
                        print("Invalid amount.")
                        continue
                if amount >= self.chips:
                    return "all-in", self.chips
                if amount < min_raise:
                    print(f"Minimum raise is ${min_raise}.")
                    continue
                if amount > max_raise:
                    print(f"Maximum raise is ${max_raise}.")
                    continue
                return "raise", amount
            else:
                print("Invalid action.")


class AIPlayer(Player):
    def choose_action(self, to_call, min_raise, max_raise, pot, current_bet=0, equity=None, num_community=5, players_in_hand=2, big_blind=10):
        if equity is None:
            equity = 0.5
        # Add noise so AI isn't perfectly predictable
        noise = random.uniform(-0.07, 0.07)
        eq = max(0.0, min(1.0, equity + noise))

        # Rare overbet/shove when facing a bet with very high equity
        if to_call > 0 and eq > 0.85:
            roll = random.random()
            if roll < 0.01:
                return ("all-in", self.chips)
            elif roll < 0.15:
                overbet = min(int(pot * 2), max_raise)
                overbet = min(overbet, self.chips)
                if overbet >= self.chips:
                    return ("all-in", self.chips)
                if overbet >= min_raise:
                    return ("raise", overbet)

        action, amount = _compute_action(eq, to_call, pot, self.chips, min_raise, max_raise, num_community)

        # Self-preservation: avoid risking elimination when many opponents remain
        if players_in_hand > 2 and random.random() < SELF_PRESERVE_CHANCE:
            preserve_floor = SELF_PRESERVE_BB * big_blind
            chips_after = self.chips - amount if action in ("raise", "call") else 0
            if action == "all-in" or (action in ("raise", "call") and chips_after < preserve_floor):
                # Downgrade: call instead of raise, fold instead of call/all-in
                if action in ("all-in", "raise"):
                    if to_call == 0:
                        return ("check", 0)
                    if to_call <= self.chips - preserve_floor:
                        return ("call", min(to_call, self.chips))
                    return ("fold", 0)
                if action == "call":
                    return ("fold", 0)

        return (action, amount)
