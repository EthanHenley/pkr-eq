from card import Deck
from equity import calculate_equity
from display import (
    render_game_state, render_action, render_showdown,
    render_winner_no_showdown, render_elimination, wait_for_enter,
)
from treys import Evaluator
from player import HumanPlayer

_evaluator = Evaluator()


class Dealer:
    def __init__(self, table, players):
        self.table = table
        self.players = players
        self.deck = Deck()

    def _active_players(self):
        return [p for p in self.players if p.is_active]

    def _players_in_hand(self):
        return [p for p in self.players if p.is_in_hand]

    def _players_can_act(self):
        return [p for p in self.players if p.is_in_hand and not p.is_all_in]

    def _rotate_dealer(self):
        active = self._active_players()
        if len(active) < 2:
            return
        # Move dealer button to next active player
        n = len(self.players)
        pos = self.table.dealer_pos
        for _ in range(n):
            pos = (pos + 1) % n
            if self.players[pos].is_active:
                self.table.dealer_pos = pos
                return

    def _get_position_order(self, start_offset=1):
        """Get players in position order starting from dealer + offset."""
        n = len(self.players)
        order = []
        pos = self.table.dealer_pos
        for _ in range(n):
            pos = (pos + start_offset) % n
            start_offset = 1
            if self.players[pos].is_in_hand:
                order.append(self.players[pos])
        return order

    def _post_blinds(self):
        active = self._active_players()
        if len(active) < 2:
            return

        n = len(self.players)
        # Small blind: first active after dealer
        pos = self.table.dealer_pos
        sb_player = None
        for _ in range(n):
            pos = (pos + 1) % n
            if self.players[pos].is_active:
                sb_player = self.players[pos]
                break

        # Big blind: next active after SB
        bb_player = None
        for _ in range(n):
            pos = (pos + 1) % n
            if self.players[pos].is_active:
                bb_player = self.players[pos]
                break

        # Post
        sb_amount = sb_player.bet(min(self.table.small_blind, sb_player.chips))
        self.table.pot += sb_amount
        sb_player.last_action = f"SB ${sb_amount}"

        bb_amount = bb_player.bet(min(self.table.big_blind, bb_player.chips))
        self.table.pot += bb_amount
        bb_player.last_action = f"BB ${bb_amount}"

        return bb_amount  # current bet to match

    def _deal_hole_cards(self):
        for p in self._players_in_hand():
            p.hole_cards = self.deck.deal(2)

    def _deal_community(self, n):
        cards = self.deck.deal(n)
        if not isinstance(cards, list):
            cards = [cards]
        self.table.community_cards.extend(cards)

    def _get_human(self):
        for p in self.players:
            if isinstance(p, HumanPlayer):
                return p
        return None

    def _compute_equity(self):
        human = self._get_human()
        if human is None or not human.is_in_hand or not human.hole_cards:
            return None
        opponents = len([p for p in self._players_in_hand() if p is not human])
        if opponents == 0:
            return 1.0
        remaining = self.deck.cards
        return calculate_equity(
            human.hole_cards,
            self.table.community_cards,
            opponents,
            remaining,
        )

    def _render(self, equity=None):
        human = self._get_human()
        if human:
            render_game_state(human, self.table, self.players, equity)

    def betting_round(self, is_preflop=False):
        if is_preflop:
            # Preflop: start from player after BB (UTG)
            order = self._get_position_order(start_offset=1)
            # In preflop, we need to start from 3rd player after dealer (UTG)
            # The first two in order are SB and BB
            if len(order) > 2:
                order = order[2:] + order[:2]
            elif len(order) == 2:
                # Heads up: SB acts first preflop
                pass
        else:
            order = self._get_position_order(start_offset=1)

        current_bet = max((p.current_bet for p in self._players_in_hand()), default=0)
        last_raiser = None
        min_raise_size = self.table.big_blind

        # Track who still needs to act
        acted = set()

        i = 0
        while i < len(order):
            p = order[i]
            if not p.is_in_hand or p.is_all_in:
                i += 1
                continue

            # If only one player can act and no bet to call, done
            can_act = self._players_can_act()
            if len(can_act) <= 1 and current_bet == 0:
                break
            if len(self._players_in_hand()) <= 1:
                break

            # If this player was the last raiser and has acted, round is over
            if p is last_raiser and p in acted:
                break

            to_call = current_bet - p.current_bet
            max_raise = p.chips
            min_raise_to = current_bet + min_raise_size

            equity = self._compute_equity()
            self._render(equity)

            action, amount = p.choose_action(to_call, min_raise_to, max_raise, self.table.pot)

            if action == "fold":
                p.fold()
                render_action(p.name, "fold")
            elif action == "check":
                p.last_action = "check"
                render_action(p.name, "check")
            elif action == "call":
                actual = p.bet(to_call)
                self.table.pot += actual
                p.last_action = f"call ${actual}"
                render_action(p.name, "call", actual)
            elif action == "raise":
                # amount is the total raise-to amount
                raise_to = amount
                additional = raise_to - p.current_bet
                actual = p.bet(additional)
                self.table.pot += actual
                new_bet = p.current_bet
                if new_bet > current_bet:
                    min_raise_size = new_bet - current_bet
                    current_bet = new_bet
                    last_raiser = p
                    # Everyone needs to act again
                    remaining_players = [x for x in order if x.is_in_hand and not x.is_all_in and x is not p]
                    # Rebuild order: continue from next player, wrap around
                    new_order = order[i+1:] + order[:i]
                    new_order = [x for x in new_order if x.is_in_hand and not x.is_all_in]
                    order = [p] + new_order  # p first so we can detect loop
                    acted = {p}
                    i = 0  # will be incremented to 1
                p.last_action = f"raise ${p.current_bet}"
                render_action(p.name, "raise", p.current_bet)
            elif action == "all-in":
                actual = p.bet(p.chips)
                self.table.pot += actual
                new_bet = p.current_bet
                if new_bet > current_bet:
                    min_raise_size = max(min_raise_size, new_bet - current_bet)
                    current_bet = new_bet
                    last_raiser = p
                    remaining_players = [x for x in order if x.is_in_hand and not x.is_all_in and x is not p]
                    new_order = order[i+1:] + order[:i]
                    new_order = [x for x in new_order if x.is_in_hand and not x.is_all_in]
                    order = [p] + new_order
                    acted = {p}
                    i = 0
                p.last_action = f"all-in ${p.current_bet}"
                render_action(p.name, "all-in", actual)

            acted.add(p)
            i += 1

            if not isinstance(p, HumanPlayer):
                import time
                time.sleep(0.3)

        # Reset per-round bets
        for p in self._players_in_hand():
            p.reset_for_round()

    def showdown(self):
        in_hand = self._players_in_hand()
        board = self.table.community_cards

        if len(in_hand) == 1:
            winner = in_hand[0]
            winner.chips += self.table.pot
            render_winner_no_showdown(winner, self.table.pot)
            return

        # Evaluate hands
        results = []
        for p in in_hand:
            score = _evaluator.evaluate(board, p.hole_cards)
            rank_class = _evaluator.get_rank_class(score)
            rank_str = _evaluator.class_to_string(rank_class)
            results.append((p, score, rank_str))

        results.sort(key=lambda x: x[1])  # lower is better
        best_score = results[0][1]
        winners = [r[0] for r in results if r[1] == best_score]

        hands_info = [(p.name, p.hole_cards, rank_str) for p, _, rank_str in results]
        render_showdown(winners, hands_info, board, self.table.pot)

        # Award pot
        share = self.table.pot // len(winners)
        remainder = self.table.pot % len(winners)
        for w in winners:
            w.chips += share
        if remainder > 0:
            winners[0].chips += remainder

    def play_hand(self):
        # Setup
        self.table.reset_for_hand()
        self._rotate_dealer()
        self.deck.shuffle()

        for p in self.players:
            p.reset_for_hand()

        active = self._active_players()
        if len(active) < 2:
            return False

        # Post blinds
        current_bet = self._post_blinds()

        # Deal hole cards
        self._deal_hole_cards()

        # Preflop
        equity = self._compute_equity()
        self._render(equity)
        wait_for_enter("Press Enter for preflop betting...")

        self.betting_round(is_preflop=True)
        if len(self._players_in_hand()) <= 1:
            self.showdown()
            return True

        # Flop
        self._deal_community(3)
        equity = self._compute_equity()
        self._render(equity)
        wait_for_enter("Press Enter for flop betting...")

        self.betting_round()
        if len(self._players_in_hand()) <= 1:
            self.showdown()
            return True

        # Turn
        self._deal_community(1)
        equity = self._compute_equity()
        self._render(equity)
        wait_for_enter("Press Enter for turn betting...")

        self.betting_round()
        if len(self._players_in_hand()) <= 1:
            self.showdown()
            return True

        # River
        self._deal_community(1)
        equity = self._compute_equity()
        self._render(equity)
        wait_for_enter("Press Enter for river betting...")

        self.betting_round()
        self.showdown()
        return True

    def eliminate_players(self):
        for p in self.players:
            if p.is_active and p.chips <= 0:
                p.is_active = False
                render_elimination(p)
