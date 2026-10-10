from poker_game.display import format_card, show_header, show_table
from poker_game.engine import PokerGame


def test_format_card_uses_plain_text_names():
    assert format_card("As") == "Ace of spades"
    assert format_card("Td") == "10 of diamonds"
    assert format_card("??") == "unknown card"


def test_header_and_table_have_no_graphical_terminal_formatting(capsys):
    game = PokerGame(["alice", "bot"])
    game.players[1]["is_bot"] = True
    game.start_round()

    show_header()
    show_table(game, "Pre-Flop")

    output = capsys.readouterr().out
    assert "Thunder Poker" in output
    assert "Board: no cards dealt yet" in output
    assert "Your hand:" not in output
    assert "\033[" not in output
    assert not any(character in output for character in "┌┐└┘│─═♠♥♦♣")
