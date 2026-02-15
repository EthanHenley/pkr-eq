from treys import Card, Deck as TreysDeck


SUIT_SYMBOLS = {
    "s": "\u2660",
    "h": "\u2665",
    "d": "\u2666",
    "c": "\u2663",
}

RANK_MAP = {
    "2": "2", "3": "3", "4": "4", "5": "5", "6": "6",
    "7": "7", "8": "8", "9": "9", "T": "T", "J": "J",
    "Q": "Q", "K": "K", "A": "A",
}


def pretty_card(card_int):
    s = Card.int_to_str(card_int)
    rank = s[0]
    suit = s[1].lower()
    return f"{RANK_MAP[rank]}{SUIT_SYMBOLS.get(suit, suit)}"


def pretty_cards(card_ints):
    return " ".join(pretty_card(c) for c in card_ints)


class Deck:
    def __init__(self):
        self._deck = TreysDeck()

    def shuffle(self):
        self._deck = TreysDeck()

    def deal(self, n=1):
        return self._deck.draw(n)

    @property
    def cards(self):
        return list(self._deck.cards)
