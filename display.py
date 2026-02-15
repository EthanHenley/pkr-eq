import os
from card import pretty_cards, pretty_card


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def render_game_state(human, table, players, equity=None, recommendation=None):
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

        pos = table.positions.get(p.name, " ")
        action_str = f"  ({p.last_action})" if p.last_action else ""
        print(f"  {pos} {p.name:12s}  ${p.chips:>6}{status}{action_str}")
    print("-" * 60)

    # Human player
    print()
    if human.hole_cards:
        print(f"  Your hand: {pretty_cards(human.hole_cards)}")
    if equity is not None:
        print(f"  Equity: {equity:.1%}")
    if recommendation:
        print(f"  Suggested: {recommendation}")
    human_pos = table.positions.get(human.name, "")
    pos_label = {"D": " (Dealer)", "S": " (Small Blind)", "B": " (Big Blind)"}.get(human_pos, "")
    print(f"  Your chips: ${human.chips}{pos_label}")

    if human.is_all_in:
        print("  ** ALL-IN **")
    print()


def render_action(player_name, action, amount=0):
    name = f"{player_name:12s}"
    you = _is_you(player_name)
    if action == "fold":
        print(f"  >> {name} {'fold' if you else 'folds'}")
    elif action == "check":
        print(f"  >> {name} {'check' if you else 'checks'}")
    elif action == "call":
        print(f"  >> {name} {'call' if you else 'calls'} ${amount}")
    elif action == "raise":
        print(f"  >> {name} {'raise' if you else 'raises'} to ${amount}")
    elif action == "all-in":
        print(f"  >> {name} {'go' if you else 'goes'} ALL-IN for ${amount}")


def _is_you(name):
    return name.lower().strip() == "you"


def render_showdown(awards, hands, board, total_pot):
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
    # Aggregate awards per player across side pots
    totals = {}
    for winner_names, amount in awards:
        if len(winner_names) == 1:
            totals[winner_names[0]] = totals.get(winner_names[0], 0) + amount
        else:
            share = amount // len(winner_names)
            for name in winner_names:
                totals[name] = totals.get(name, 0) + share
    for name, amount in totals.items():
        print(f"  >> {name} {'win' if _is_you(name) else 'wins'} ${amount}")
    print()


def render_winner_no_showdown(winner, pot):
    print(f"\n  >> Everyone folds. {winner.name} {'win' if _is_you(winner.name) else 'wins'} ${pot}\n")


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
