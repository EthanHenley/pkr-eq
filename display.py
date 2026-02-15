import os
from card import pretty_cards, pretty_card


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def render_game_state(human, table, players, equity=None):
    clear_screen()
    print("=" * 60)
    print(f"  TEXAS HOLD'EM  |  Hand #{table.hand_count}  |  Blinds: ${table.small_blind}/${table.big_blind}")
    print("=" * 60)

    # Community cards
    if table.community_cards:
        print(f"\n  Board: {pretty_cards(table.community_cards)}")
    else:
        print("\n  Board: --")

    print(f"  Pot: ${table.pot}")
    print()

    # Other players
    print("-" * 60)
    for p in players:
        if p is human:
            continue
        status = ""
        if not p.is_active:
            status = " [ELIMINATED]"
        elif not p.is_in_hand:
            status = " [FOLDED]"
        elif p.is_all_in:
            status = " [ALL-IN]"

        action_str = f"  ({p.last_action})" if p.last_action else ""
        print(f"  {p.name:12s}  ${p.chips:>6}{status}{action_str}")
    print("-" * 60)

    # Human player
    print()
    if human.hole_cards:
        print(f"  Your hand: {pretty_cards(human.hole_cards)}")
    if equity is not None:
        print(f"  Equity: {equity:.1%}")
    print(f"  Your chips: ${human.chips}")

    if human.is_all_in:
        print("  ** ALL-IN **")
    print()


def render_action(player_name, action, amount=0):
    name = f"{player_name:12s}"
    if action == "fold":
        print(f"  >> {name} folds")
    elif action == "check":
        print(f"  >> {name} checks")
    elif action == "call":
        print(f"  >> {name} calls ${amount}")
    elif action == "raise":
        print(f"  >> {name} raises to ${amount}")
    elif action == "all-in":
        print(f"  >> {name} goes ALL-IN for ${amount}")


def render_showdown(winners, hands, board, pot):
    print("\n" + "=" * 60)
    print("  SHOWDOWN")
    print("=" * 60)
    print(f"  Board: {pretty_cards(board)}")
    print()
    max_name = max(len(name) for name, _, _ in hands)
    pad = max(max_name, 12)
    for name, cards, rank_str in hands:
        print(f"  {name:{pad}s}  {pretty_cards(cards)}  ({rank_str})")
    print()
    if len(winners) == 1:
        print(f"  >> {winners[0].name} wins ${pot}")
    else:
        split = pot // len(winners)
        names = ", ".join(w.name for w in winners)
        print(f"  >> Split pot: {names} each win ${split}")
    print()


def render_winner_no_showdown(winner, pot):
    print(f"\n  >> Everyone folds. {winner.name} wins ${pot}\n")


def render_elimination(player):
    if player.name.lower().strip()=="you":
        print(f"  !! {player.name} have been eliminated !!")
    else:
        print(f"  !! {player.name} has been eliminated !!")


def render_chip_counts(players):
    print("\n  -- Chip Counts --")
    active = sorted([p for p in players if p.is_active], key=lambda p: -p.chips)
    for i, p in enumerate(active, 1):
        print(f"  {i}. {p.name:12s}  ${p.chips}")
    print()


def wait_for_enter(msg="Press Enter to continue..."):
    input(f"  {msg}")
