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
    def choose_action(self, to_call, min_raise, max_raise, pot, current_bet=0):
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
    def choose_action(self, to_call, min_raise, max_raise, pot, current_bet=0):
        if to_call == 0:
            # No bet to call: check, bet, or all-in
            r = random.random()
            if r < 0.50:
                return "check", 0
            elif r < 0.80:
                amount = random.randint(min_raise, min(max_raise, pot))
                if amount >= self.chips:
                    return "all-in", self.chips
                return "raise", amount
            elif r < 0.95:
                amount = random.randint(min_raise, max_raise)
                if amount >= self.chips:
                    return "all-in", self.chips
                return "raise", amount
            else:
                return "all-in", self.chips
        else:
            # Facing a bet
            r = random.random()
            if r < 0.45:
                if to_call >= self.chips:
                    return "all-in", self.chips
                return "call", min(to_call, self.chips)
            elif r < 0.70:
                return "fold", 0
            elif r < 0.90:
                if min_raise > max_raise:
                    # Can only call or fold
                    return "call", min(to_call, self.chips)
                amount = random.randint(min_raise, min(max_raise, max(min_raise, to_call * 3)))
                if amount >= self.chips:
                    return "all-in", self.chips
                return "raise", amount
            else:
                return "all-in", self.chips
