class Table:
    def __init__(self, small_blind=5, big_blind=10, escalate_every=10):
        self.community_cards = []
        self.pot = 0
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.escalate_every = escalate_every
        self.hand_count = 0
        self.dealer_pos = 0

    def escalate_blinds(self):
        self.small_blind *= 2
        self.big_blind *= 2

    def reset_for_hand(self):
        self.community_cards = []
        self.pot = 0
        self.hand_count += 1
        if self.hand_count > 0 and self.hand_count % self.escalate_every == 0:
            self.escalate_blinds()
            print(f"\n  ** Blinds increasing to ${self.small_blind}/${self.big_blind} **\n")
