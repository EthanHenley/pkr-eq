import argparse
from player import HumanPlayer, AIPlayer
from table import Table
from dealer import Dealer
from display import render_chip_counts, clear_screen, wait_for_enter
import display


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cheat", action="store_true", help="Show opponent hands and equities")
    args = parser.parse_args()

    display.CHEAT_MODE = args.cheat

    print("\n  Welcome to Texas Hold'em Tournament Simulator!")
    print("  9 players | $1000 starting stacks | $5/$10 blinds\n")
    if args.cheat:
        print("  ** CHEATER MODE ENABLED **\n")

    players = [HumanPlayer("You", 1000)]
    for i in range(1, 9):
        players.append(AIPlayer(f"Player {i}", 1000))

    table = Table(small_blind=5, big_blind=10, escalate_every=10)
    dealer = Dealer(table, players)

    while True:
        active = [p for p in players if p.is_active]
        if len(active) < 2:
            break

        human = players[0]
        if not human.is_active:
            print("\n  You have been eliminated. Game over!\n")
            break

        if not dealer.play_hand():
            break

        dealer.eliminate_players()

        active = [p for p in players if p.is_active]
        if len(active) == 1:
            print(f"\n  {active[0].name} wins the tournament!\n")
            break

        render_chip_counts(players)
        wait_for_enter()


if __name__ == "__main__":
    main()
