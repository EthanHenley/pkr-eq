import argparse
from player import HumanPlayer, AIPlayer
from table import Table
from dealer import Dealer
from display import render_chip_counts, clear_screen, wait_for_enter
import display

SMALL_BLIND = 10
BIG_BLIND = 20
ESCALATE_EVERY = 10
START_STACK = 1000

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cheat", action="store_true", help="Show opponent hands and equities")
    args = parser.parse_args()

    display.CHEAT_MODE = args.cheat

    print("\n  Welcome to Texas Hold'em Tournament Simulator!")
    print(f"  9 players | ${START_STACK} starting stacks | ${SMALL_BLIND}/${BIG_BLIND} blinds\n")
    if args.cheat:
        print("  ** CHEATER MODE ENABLED **\n")

    players = [HumanPlayer("You", START_STACK)]
    for i in range(1, 9):
        players.append(AIPlayer(f"Player {i}", START_STACK))

    table = Table(small_blind=SMALL_BLIND, big_blind=BIG_BLIND, escalate_every=ESCALATE_EVERY)
    dealer = Dealer(table, players)

    while True:
        active = [p for p in players if p.is_active]
        if len(active) < 2:
            break

        human = players[0]
        if not human.is_active:
            if display.CHEAT_MODE:
                choice = input("\n  You have been eliminated. Buy back in? [y/n]: ").strip().lower()
                if choice == "y":
                    human.chips = START_STACK
                    human.is_active = True
                    print(f"  Bought back in for ${START_STACK}.\n")
                else:
                    print("\n  Game over!\n")
                    break
            else:
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
