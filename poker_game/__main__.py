"""Thunder Poker — text-only game loop."""

import sys

from .display import (
    prompt_action,
    show_action_log,
    show_header,
    show_scoreboard,
    show_showdown,
    show_table,
    show_winner,
    show_your_hand,
)
from .engine import PokerGame


SMALL_BLIND = 10
BIG_BLIND = 20
STARTING_CHIPS = 1000


def get_human_action(game, player_index):
    """Prompt the human player for an action."""
    show_your_hand(game.players[player_index])
    return prompt_action(game, player_index)


def run_street(game, street_name, human_index):
    """Display the state and complete betting for one street."""
    show_header()
    show_table(game, street_name, current_player=human_index)
    show_action_log(game.action_log, max_lines=4)

    if game.active_player_count() <= 1:
        return

    show_your_hand(game.players[human_index])
    game.begin_betting_round()
    game.run_betting_round(human_index, get_human_action)

    show_table(game, street_name)
    show_action_log(game.action_log, max_lines=6)


def play_hand(game, human_index):
    """Play a complete hand from the blinds through showdown."""
    game.start_round()
    game.post_blinds(SMALL_BLIND, BIG_BLIND)

    run_street(game, "Pre-Flop", human_index)
    if game.active_player_count() <= 1:
        return _finish_hand(game)

    game.deal_flop()
    run_street(game, "Flop", human_index)
    if game.active_player_count() <= 1:
        return _finish_hand(game)

    game.deal_turn()
    run_street(game, "Turn", human_index)
    if game.active_player_count() <= 1:
        return _finish_hand(game)

    game.deal_river()
    run_street(game, "River", human_index)
    return _finish_hand(game, showdown=True)


def _finish_hand(game, showdown=False):
    """Resolve the hand, award the pot, and display the result."""
    show_header()
    if showdown and game.active_player_count() > 1:
        show_showdown(game)

    winner_info = game.winner()
    show_winner(winner_info)
    show_action_log(game.action_log, max_lines=8)
    return winner_info


def welcome_screen():
    """Get the human player's name and the number of bot opponents."""
    show_header()
    print("Welcome to Thunder Poker!")
    print("A Texas Hold'em experience")

    name = input("Enter your name (or press Enter for 'Player'): ").strip()
    if not name:
        name = "Player"

    num_bots_str = input("Number of bot opponents (1-5, default 3): ").strip()
    try:
        num_bots = max(1, min(5, int(num_bots_str)))
    except ValueError:
        num_bots = 3

    bot_names = ["Bot Ace", "Bot King", "Bot Queen", "Bot Jack", "Bot Ten"][:num_bots]
    return name, bot_names


def main():
    """Run the text-only poker game."""
    try:
        player_name, bot_names = welcome_screen()
    except (EOFError, KeyboardInterrupt):
        print("\nGoodbye!")
        sys.exit(0)

    game = PokerGame([player_name] + bot_names, starting_chips=STARTING_CHIPS)
    for player in game.players[1:]:
        player["is_bot"] = True

    main_console(game, human_index=0)


def main_console(game, human_index):
    """Run consecutive hands through the terminal."""
    hand_number = 0

    while True:
        hand_number += 1

        if game.players[human_index]["chips"] <= 0:
            print("You are out of chips. Game over.")
            show_scoreboard(game.players)
            break

        alive = [player for player in game.players if player["chips"] > 0]
        if len(alive) <= 1:
            print(f"{alive[0]['name']} is the last player standing.")
            show_scoreboard(game.players)
            break

        print()
        print(f"Hand {hand_number}")
        print(
            f"Blinds: {SMALL_BLIND}/{BIG_BLIND} | "
            f"Dealer: {game.players[game.dealer_index]['name']}"
        )

        try:
            input("Press Enter to deal... ")
            play_hand(game, human_index)
        except (EOFError, KeyboardInterrupt):
            print("\nGame interrupted.")
            break

        show_scoreboard(game.players)
        try:
            cont = input("Play another hand? (y/n, default y): ").strip().lower()
            if cont == "n":
                break
        except (EOFError, KeyboardInterrupt):
            break

        game.rotate_dealer()

    print()
    print("Thanks for playing Thunder Poker!")


if __name__ == "__main__":
    main()
