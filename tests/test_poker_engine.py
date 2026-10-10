import pytest

from poker_game.engine import PokerGame, evaluate_hand, compare_hands, hand_name


@pytest.mark.parametrize(
    "cards, expected_rank",
    [
        (["As", "Ks", "Qs", "Js", "Ts", "2d", "3c"], 10),
        (["9h", "8h", "7h", "6h", "5h", "2d", "3c"], 9),
        (["Ah", "Kh", "Qh", "Jh", "9h", "2d", "3c"], 6),
        (["Kd", "Kd", "9c", "9h", "9s", "2d", "3c"], 7),
        (["Ah", "As", "Kc", "Kd", "Qd", "2d", "3c"], 3),
    ],
)
def test_evaluate_hand_rank(cards, expected_rank):
    assert evaluate_hand(cards)[0] == expected_rank


def test_compare_hands_prefers_highest_rank():
    hand_one = ["Ah", "Ks", "Qd", "Jc", "10s", "2d", "3c"]
    hand_two = ["Kh", "Qs", "Jd", "9c", "8s", "2d", "3c"]
    assert compare_hands(hand_one, hand_two) > 0


def test_new_game_deals_two_cards_per_player():
    game = PokerGame(["alice", "bob", "charlie"], starting_chips=1000)
    game.start_round()

    assert len(game.players) == 3
    assert all(len(player["hole_cards"]) == 2 for player in game.players)
    assert len(game.community_cards) == 0


def test_round_advance_deals_flop_turn_and_river():
    game = PokerGame(["alice", "bob"], starting_chips=1000)
    game.start_round()

    game.deal_flop()
    assert len(game.community_cards) == 3

    game.deal_turn()
    assert len(game.community_cards) == 4

    game.deal_river()
    assert len(game.community_cards) == 5


def test_betting_updates_pot_and_chips():
    game = PokerGame(["alice", "bot"], starting_chips=100)
    game.start_round()
    game.begin_betting_round()

    game.place_bet(0, "raise", 20)
    game.place_bet(1, "call")

    assert game.pot == 40
    assert game.players[0]["chips"] == 80
    assert game.players[1]["chips"] == 80
    assert game.current_bet == 20


def test_folding_player_is_ignored_in_winner_selection():
    game = PokerGame(["alice", "bot"], starting_chips=100)
    game.start_round()
    game.players[1]["folded"] = True

    winner = game.winner()
    assert winner["name"] == "alice"


def test_bot_decision_returns_valid_action():
    game = PokerGame(["alice", "bot"], starting_chips=100)
    game.start_round()

    action = game.bot_decision(1)
    assert action in {"check", "call", "raise", "fold"}


# ── New Phase 2 tests ────────────────────────────────────────────────────────


def test_post_blinds_deducts_chips_and_seeds_pot():
    game = PokerGame(["alice", "bob", "charlie"], starting_chips=1000)
    game.start_round()
    game.dealer_index = 0

    sb_idx, bb_idx = game.post_blinds(10, 20)

    assert sb_idx == 1  # Player after dealer
    assert bb_idx == 2
    assert game.players[1]["chips"] == 990
    assert game.players[1]["bet"] == 10
    assert game.players[2]["chips"] == 980
    assert game.players[2]["bet"] == 20
    assert game.pot == 30
    assert game.current_bet == 20


def test_post_blinds_heads_up():
    """In heads-up (2 players), dealer posts SB and other posts BB."""
    game = PokerGame(["alice", "bob"], starting_chips=500)
    game.start_round()
    game.dealer_index = 0

    sb_idx, bb_idx = game.post_blinds(10, 20)

    assert sb_idx == 0  # Dealer is SB in heads-up
    assert bb_idx == 1
    assert game.players[0]["chips"] == 490
    assert game.players[1]["chips"] == 480
    assert game.pot == 30


def test_begin_betting_round_does_not_unfold_players():
    game = PokerGame(["alice", "bob", "charlie"], starting_chips=100)
    game.start_round()

    game.players[1]["folded"] = True
    game.begin_betting_round()

    assert game.players[1]["folded"] is True
    assert game.players[0]["folded"] is False


def test_winner_receives_pot_chips():
    game = PokerGame(["alice", "bob"], starting_chips=100)
    game.start_round()
    game.begin_betting_round()

    game.place_bet(0, "raise", 30)
    game.place_bet(1, "call")

    # Force alice to have a better hand (fold bob)
    game.players[1]["folded"] = True

    starting_chips = game.players[0]["chips"]
    pot = game.pot
    winner = game.winner()

    assert winner["name"] == "alice"
    assert game.players[0]["chips"] == starting_chips + pot
    assert game.pot == 0


def test_hand_name_returns_correct_labels():
    assert hand_name((10, 14)) == "Royal Flush"
    assert hand_name((9, 10)) == "Straight Flush"
    assert hand_name((8, 14, 13)) == "Four of a Kind"
    assert hand_name((7, 14, 13)) == "Full House"
    assert hand_name((6, 14, 13, 12, 11, 9)) == "Flush"
    assert hand_name((5, 14)) == "Straight"
    assert hand_name((4, 14, 13, 12)) == "Three of a Kind"
    assert hand_name((3, 14, 13, 12)) == "Two Pair"
    assert hand_name((2, 14, 13, 12, 11)) == "One Pair"
    assert hand_name((1, 14, 13, 12, 11, 10)) == "High Card"


def test_hand_name_handles_edge_cases():
    assert hand_name((0, 14, 13)) == "Incomplete Hand"
    assert hand_name(None) == "Unknown"
    assert hand_name(()) == "Unknown"


def test_bot_does_not_fold_when_can_check():
    """Bot should never fold when checking is free."""
    game = PokerGame(["alice", "bot"], starting_chips=100)
    game.start_round()
    game.current_bet = 0

    # Run many trials to ensure bot never folds when check is free
    for _ in range(50):
        game.current_bet = 0
        for p in game.players:
            p["bet"] = 0
        action = game._bot_action(1)
        if isinstance(action, tuple):
            assert action[0] != "fold"
        else:
            assert action != "fold"


def test_rotate_dealer():
    game = PokerGame(["alice", "bob", "charlie"], starting_chips=100)
    game.dealer_index = 0

    game.rotate_dealer()
    assert game.dealer_index == 1

    game.rotate_dealer()
    assert game.dealer_index == 2

    game.rotate_dealer()
    assert game.dealer_index == 0


def test_action_log_records_actions():
    game = PokerGame(["alice", "bob"], starting_chips=100)
    game.start_round()
    game.begin_betting_round()

    game.place_bet(0, "raise", 20)
    game.place_bet(1, "call")

    assert len(game.action_log) >= 2
    assert any("raise" in entry.lower() for entry in game.action_log)
    assert any("call" in entry.lower() for entry in game.action_log)


def test_active_player_count():
    game = PokerGame(["alice", "bob", "charlie"], starting_chips=100)
    game.start_round()

    assert game.active_player_count() == 3

    game.players[1]["folded"] = True
    assert game.active_player_count() == 2

    game.players[2]["folded"] = True
    assert game.active_player_count() == 1
