from card import Deck
from equity import calculate_equity
from display import (
    render_game_state, render_action, render_showdown,
    render_winner_no_showdown, render_elimination, wait_for_enter,
)
from treys import Evaluator
from player import HumanPlayer, recommend_action

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

    def _add_to_pot(self, player, amount):
        self.table.pot += amount
        self.table.contributions[player.name] = self.table.contributions.get(player.name, 0) + amount

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

        # Record positions
        self.table.positions[self.players[self.table.dealer_pos].name] = "D"
        self.table.positions[sb_player.name] = "S"
        self.table.positions[bb_player.name] = "B"

        # Post
        sb_amount = sb_player.bet(min(self.table.small_blind, sb_player.chips))
        self._add_to_pot(sb_player, sb_amount)
        sb_player.last_action = f"SB ${sb_amount}"

        bb_amount = bb_player.bet(min(self.table.big_blind, bb_player.chips))
        self._add_to_pot(bb_player, bb_amount)
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

    def _compute_human_equity(self):
        """Cheap single-player equity for the human (used for display)."""
        human = self._get_human()
        if human is None or not human.is_in_hand or not human.hole_cards:
            return None
        opponents = len([p for p in self._players_in_hand() if p is not human])
        if opponents == 0:
            return 1.0
        return calculate_equity(
            human.hole_cards,
            self.table.community_cards,
            opponents,
            self.deck.cards,
        )

    def _ensure_equities(self):
        """Compute per-player equities lazily, caching by board state.

        Each player's equity is calculated from their own perspective:
        only their hole cards + community cards, opponents treated as random.
        """
        board_key = tuple(self.table.community_cards)
        if getattr(self, '_equities_board_key', None) == board_key:
            return  # already computed for this board
        in_hand = self._players_in_hand()
        if len(in_hand) < 2:
            self.table.equities = {p.name: 1.0 for p in in_hand}
        else:
            remaining = self.deck.cards
            opponents = len(in_hand) - 1
            for p in in_hand:
                if p.hole_cards:
                    self.table.equities[p.name] = calculate_equity(
                        p.hole_cards, self.table.community_cards,
                        opponents, remaining,
                    )
        self._equities_board_key = board_key

    def _render(self, equity=None, recommendation=None, to_call=0, min_bet=0):
        human = self._get_human()
        if human:
            render_game_state(human, self.table, self.players, equity, recommendation, to_call, min_bet)

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

            equity = self._compute_human_equity()
            rec = None
            if isinstance(p, HumanPlayer) and equity is not None:
                rec = recommend_action(equity, to_call, self.table.pot, p.chips, min_raise_to, max_raise, num_community=len(self.table.community_cards), current_bet=current_bet, players_in_hand=len(self._players_in_hand()))
            self._render(equity, rec, to_call if isinstance(p, HumanPlayer) else 0, min_raise_to if isinstance(p, HumanPlayer) else 0)

            if not isinstance(p, HumanPlayer):
                self._ensure_equities()

            equity_val = self.table.equities.get(p.name, 0.5) if not isinstance(p, HumanPlayer) else None
            action, amount = p.choose_action(to_call, min_raise_to, max_raise, self.table.pot, current_bet, equity=equity_val, num_community=len(self.table.community_cards), players_in_hand=len(self._players_in_hand()), big_blind=self.table.big_blind)

            if action == "fold":
                p.fold()
                render_action(p.name, "fold")
            elif action == "check":
                p.last_action = "check"
                render_action(p.name, "check")
            elif action == "call":
                actual = p.bet(to_call)
                self._add_to_pot(p, actual)
                p.last_action = f"call ${actual}"
                render_action(p.name, "call", actual)
            elif action == "raise":
                # amount is the total raise-to amount
                raise_to = amount
                additional = raise_to - p.current_bet
                actual = p.bet(additional)
                self._add_to_pot(p, actual)
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
                self._add_to_pot(p, actual)
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

    def _build_side_pots(self):
        contributions = self.table.contributions
        in_hand = self._players_in_hand()
        # Include folded players' contributions too (they just aren't eligible)
        entries = sorted(
            ((name, amt) for name, amt in contributions.items()),
            key=lambda x: x[1],
        )
        eligible_names = {p.name for p in in_hand}
        pots = []
        allocated = 0
        for i, (_, level) in enumerate(entries):
            if level <= allocated:
                continue
            slice_per_player = level - allocated
            # Every player who contributed >= this level pays into this pot
            contributors = [name for name, amt in entries if amt > allocated]
            pot_amount = slice_per_player * len(contributors)
            eligible = [name for name in contributors if name in eligible_names]
            pots.append((pot_amount, eligible))
            allocated = level
        return pots

    def showdown(self):
        in_hand = self._players_in_hand()
        board = self.table.community_cards

        if len(in_hand) == 1:
            winner = in_hand[0]
            winner.chips += self.table.pot
            render_winner_no_showdown(winner, self.table.pot)
            return

        # Evaluate hands
        results = {}
        hands_info = []
        for p in in_hand:
            score = _evaluator.evaluate(board, p.hole_cards)
            rank_class = _evaluator.get_rank_class(score)
            rank_str = _evaluator.class_to_string(rank_class)
            results[p.name] = (p, score)
            hands_info.append((p.name, p.hole_cards, rank_str))

        # Build side pots and award each
        side_pots = self._build_side_pots()
        awards = []  # list of (winner_names, amount)
        for pot_amount, eligible in side_pots:
            if not eligible:
                continue
            best_score = min(results[name][1] for name in eligible if name in results)
            pot_winners = [name for name in eligible if name in results and results[name][1] == best_score]
            share = pot_amount // len(pot_winners)
            remainder = pot_amount % len(pot_winners)
            for name in pot_winners:
                results[name][0].chips += share
            if remainder > 0:
                results[pot_winners[0]][0].chips += remainder
            awards.append((pot_winners, pot_amount))

        render_showdown(awards, hands_info, board, self.table.pot)

    def play_hand(self):
        # Setup
        self.table.reset_for_hand()
        self._equities_board_key = None
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
        equity = self._compute_human_equity()
        self._render(equity)
        wait_for_enter("Press Enter for preflop betting...")

        self.betting_round(is_preflop=True)
        if len(self._players_in_hand()) <= 1:
            self.showdown()
            return True

        # Flop
        self._deal_community(3)
        equity = self._compute_human_equity()
        self._render(equity)
        wait_for_enter("Press Enter for flop betting...")

        self.betting_round()
        if len(self._players_in_hand()) <= 1:
            self.showdown()
            return True

        # Turn
        self._deal_community(1)
        equity = self._compute_human_equity()
        self._render(equity)
        wait_for_enter("Press Enter for turn betting...")

        self.betting_round()
        if len(self._players_in_hand()) <= 1:
            self.showdown()
            return True

        # River
        self._deal_community(1)
        equity = self._compute_human_equity()
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
