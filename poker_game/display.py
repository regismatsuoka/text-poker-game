"""Plain-text display and input helpers for Thunder Poker."""

from .engine import evaluate_hand, hand_name


RANK_NAMES = {
    "2": "2",
    "3": "3",
    "4": "4",
    "5": "5",
    "6": "6",
    "7": "7",
    "8": "8",
    "9": "9",
    "T": "10",
    "J": "Jack",
    "Q": "Queen",
    "K": "King",
    "A": "Ace",
}
SUIT_NAMES = {
    "s": "spades",
    "h": "hearts",
    "d": "diamonds",
    "c": "clubs",
}


def format_card(card):
    """Format a card such as ``As`` as plain text."""
    if card is None or card == "??":
        return "unknown card"
    return f"{RANK_NAMES.get(card[:-1], card[:-1])} of {SUIT_NAMES.get(card[-1], 'unknown suit')}"


def show_header():
    """Print the game title."""
    print()
    print("Thunder Poker")
    print("Texas Hold'em")


def show_community_cards(cards, street_name=""):
    """Display the community cards with a street label."""
    label = street_name or "Board"
    card_text = ", ".join(format_card(card) for card in cards) if cards else "no cards dealt yet"
    print(f"{label}: {card_text}")


def show_pot(pot, current_bet=0):
    """Display the pot amount."""
    text = f"Pot: {pot}"
    if current_bet > 0:
        text += f" | Current bet: {current_bet}"
    print(text)


def show_player(player, index, is_dealer=False, is_current=False, reveal=False):
    """Display a single player's status and, when appropriate, cards."""
    del index
    details = [player["name"]]
    if is_dealer:
        details.append("dealer")
    if is_current:
        details.append("to act")
    if player["folded"]:
        details.append("folded")
    else:
        details.append(f"chips: {player['chips']}")
        if player["bet"] > 0:
            details.append(f"bet: {player['bet']}")

    print(" - ".join(details))
    if reveal and player["hole_cards"]:
        cards = ", ".join(format_card(card) for card in player["hole_cards"])
        print(f"  Cards: {cards}")


def show_table(game, street_name="", reveal_all=False, current_player=None):
    """Display the current table state as plain text."""
    print()
    print(f"Table - {street_name}" if street_name else "Table")
    show_pot(game.pot, game.current_bet)
    show_community_cards(game.community_cards)

    for idx, player in enumerate(game.players):
        reveal = reveal_all or (idx == 0 and not player.get("is_bot", True))
        show_player(
            player,
            idx,
            is_dealer=idx == game.dealer_index,
            is_current=idx == current_player,
            reveal=reveal,
        )


def show_action_log(log, max_lines=5):
    """Display the most recent action log entries."""
    if not log:
        return
    print("Recent actions:")
    for entry in log[-max_lines:]:
        print(f"  {entry}")


def show_showdown(game):
    """Reveal active hands and their evaluated names."""
    print()
    print("Showdown")
    show_community_cards(game.community_cards, "Final board")

    for player in game.players:
        if player["folded"]:
            continue
        score = evaluate_hand(player["hole_cards"] + game.community_cards)
        cards = ", ".join(format_card(card) for card in player["hole_cards"])
        print(f"{player['name']}: {hand_name(score)} ({cards})")


def show_winner(winner_info):
    """Announce the round winner."""
    hand = hand_name(winner_info["score"])
    pot = winner_info.get("pot_awarded", 0)
    print(f"{winner_info['name']} wins {pot} chips with {hand}.")


def show_scoreboard(players):
    """Display chip standings for all players."""
    print()
    print("Chip standings:")
    sorted_players = sorted(players, key=lambda player: player["chips"], reverse=True)
    for rank, player in enumerate(sorted_players, 1):
        print(f"{rank}. {player['name']}: {player['chips']} chips")


def show_your_hand(player):
    """Show the human player's hole cards."""
    print()
    cards = ", ".join(format_card(card) for card in player["hole_cards"])
    print(f"Your hand: {cards or 'not dealt'}")


def prompt_action(game, player_index):
    """Prompt a human player for their action."""
    player = game.players[player_index]
    cost_to_call = game.current_bet - player["bet"]

    print(f"{player['name']}'s turn")
    print(f"Chips: {player['chips']} | To call: {cost_to_call}")

    if cost_to_call == 0:
        print("  [C]heck")
    else:
        print(f"  [C]all ({cost_to_call})")
    print("  [R]aise")
    print("  [F]old")

    while True:
        choice = input("Action: ").strip().lower()

        if choice in ("c", "check") and cost_to_call == 0:
            return "check"
        if choice in ("c", "call") and cost_to_call > 0:
            return "call"
        if choice in ("r", "raise"):
            while True:
                try:
                    amount = int(input("Raise amount: ").strip())
                    if amount <= 0:
                        print("Amount must be positive.")
                        continue
                    if amount > player["chips"]:
                        print(f"Maximum you can bet: {player['chips']}")
                        continue
                    return ("raise", amount)
                except ValueError:
                    print("Enter a valid number.")
        if choice in ("f", "fold"):
            return "fold"
        print("Invalid action. Try again.")
