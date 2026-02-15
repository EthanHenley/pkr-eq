import random


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


class HumanPlayer(Player):
    def choose_action(self, to_call, min_raise, max_raise, pot, current_bet=0, equity=None):
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
    def choose_action(self, to_call, min_raise, max_raise, pot, current_bet=0, equity=None):
        if equity is None:
            equity = 0.5
        # Add noise so AI isn't perfectly predictable
        noise = random.uniform(-0.07, 0.07)
        eq = max(0.0, min(1.0, equity + noise))

        if to_call == 0:
            # No bet to face — can check or bet
            if eq < 0.35:
                # Weak hand: usually check, small bluff chance
                if random.random() < 0.1:
                    return self._make_bet(min_raise, max_raise, pot, fraction=0.4)
                return "check", 0
            elif eq < 0.6:
                # Medium hand: bet small sometimes, check otherwise
                if random.random() < 0.5:
                    return self._make_bet(min_raise, max_raise, pot, fraction=0.5)
                return "check", 0
            else:
                # Strong hand: bet, small slowplay chance
                if random.random() < 0.1:
                    return "check", 0
                fraction = 0.5 + (eq - 0.6) / 0.4 * 0.5  # 0.5–1.0 of pot
                return self._make_bet(min_raise, max_raise, pot, fraction=fraction)
        else:
            # Facing a bet
            pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0.5

            # All-in decision when pot-committed
            if to_call >= self.chips:
                if eq >= pot_odds:
                    return "all-in", self.chips
                else:
                    return "fold", 0

            # Strong value all-in
            if eq > 0.85 and random.random() < 0.15:
                return "all-in", self.chips

            if eq < pot_odds * 0.8:
                # Not enough equity to continue
                return "fold", 0
            elif eq < 0.6:
                # Adequate equity — call
                return "call", min(to_call, self.chips)
            else:
                # Strong hand — raise
                if min_raise > max_raise:
                    return "call", min(to_call, self.chips)
                # Scale raise with equity
                frac = (eq - 0.6) / 0.4  # 0.0–1.0
                raise_to = int(min_raise + (max_raise - min_raise) * frac)
                raise_to = max(min_raise, min(raise_to, max_raise))
                if raise_to >= self.chips:
                    return "all-in", self.chips
                return "raise", raise_to

    def _make_bet(self, min_raise, max_raise, pot, fraction=0.5):
        """Helper to construct a bet/raise of a fraction of the pot."""
        if min_raise > max_raise:
            return "check", 0
        target = max(min_raise, int(pot * fraction))
        target = max(min_raise, min(target, max_raise))
        if target >= self.chips:
            return "all-in", self.chips
        return "raise", target
