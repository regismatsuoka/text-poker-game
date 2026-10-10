import random
from collections import Counter
from itertools import combinations


RANK_ORDER = {
    "2": 2,
    "3": 3,
    "4": 4,
    "5": 5,
    "6": 6,
    "7": 7,
    "8": 8,
    "9": 9,
    "T": 10,
    "J": 11,
    "Q": 12,
    "K": 13,
    "A": 14,
}

SUITS = ["s", "h", "d", "c"]
VALUES = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]

HAND_RANK_NAMES = {
    10: "Royal Flush",
    9: "Straight Flush",
    8: "Four of a Kind",
    7: "Full House",
    6: "Flush",
    5: "Straight",
    4: "Three of a Kind",
    3: "Two Pair",
    2: "One Pair",
    1: "High Card",
    0: "Incomplete Hand",
}


def hand_name(score):
    """Return a human-readable name for a hand evaluation score tuple."""
    if not score:
        return "Unknown"
    rank = score[0]
    return HAND_RANK_NAMES.get(rank, "Unknown")


class Deck:
    def __init__(self):
        self.cards = self._create_deck()

    @staticmethod
    def _create_deck():
        deck = []
        for value in VALUES:
            for suit in SUITS:
                deck.append(f"{value}{suit}")
        return deck

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self):
        if not self.cards:
            raise ValueError("No cards left in the deck.")
        return self.cards.pop()


class PokerGame:
    def __init__(self, players, starting_chips=1000):
        self.players = [
            {
                "name": player,
                "chips": starting_chips,
                "hole_cards": [],
                "folded": False,
                "bet": 0,
                "is_bot": False,
            }
            for player in players
        ]
        self.deck = Deck()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.active_players = list(range(len(self.players)))
        self.dealer_index = 0
        self.action_log = []

    def _log(self, message):
        """Append a message to the action log."""
        self.action_log.append(message)

    def _next_seat(self, seat, skip_folded=False):
        """Return the next seat index, wrapping around. Optionally skip folded players."""
        n = len(self.players)
        for offset in range(1, n + 1):
            idx = (seat + offset) % n
            if skip_folded and self.players[idx]["folded"]:
                continue
            return idx
        return seat

    def rotate_dealer(self):
        """Move the dealer button to the next player with chips."""
        n = len(self.players)
        for offset in range(1, n + 1):
            idx = (self.dealer_index + offset) % n
            if self.players[idx]["chips"] > 0:
                self.dealer_index = idx
                return
        # Fallback: just advance by one
        self.dealer_index = (self.dealer_index + 1) % n

    def post_blinds(self, small_blind=10, big_blind=20):
        """Post small and big blinds from the players after the dealer."""
        n = len(self.players)
        if n == 2:
            sb_index = self.dealer_index
            bb_index = self._next_seat(self.dealer_index)
        else:
            sb_index = self._next_seat(self.dealer_index)
            bb_index = self._next_seat(sb_index)

        sb_player = self.players[sb_index]
        bb_player = self.players[bb_index]

        sb_amount = min(small_blind, sb_player["chips"])
        bb_amount = min(big_blind, bb_player["chips"])

        sb_player["chips"] -= sb_amount
        sb_player["bet"] = sb_amount
        self.pot += sb_amount

        bb_player["chips"] -= bb_amount
        bb_player["bet"] = bb_amount
        self.pot += bb_amount

        self.current_bet = bb_amount

        self._log(f"{sb_player['name']} posts small blind ({sb_amount})")
        self._log(f"{bb_player['name']} posts big blind ({bb_amount})")

        return sb_index, bb_index

    def start_round(self):
        self.deck = Deck()
        self.deck.shuffle()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.action_log = []
        self.active_players = list(range(len(self.players)))
        for player in self.players:
            player["hole_cards"] = []
            player["folded"] = False
            player["bet"] = 0

        for _ in range(2):
            for player in self.players:
                player["hole_cards"].append(self.deck.draw())

    def begin_betting_round(self):
        """Reset per-round bet tracking without touching fold status."""
        self.current_bet = 0
        for player in self.players:
            player["bet"] = 0

    def _apply_bet(self, player_index, amount):
        player = self.players[player_index]
        amount = min(amount, player["chips"])
        player["chips"] -= amount
        player["bet"] += amount
        self.pot += amount
        self.current_bet = max(self.current_bet, player["bet"])
        return amount

    def place_bet(self, player_index, action, amount=None):
        player = self.players[player_index]
        action = action.lower()

        if player["folded"]:
            return 0

        if action == "fold":
            player["folded"] = True
            self._log(f"{player['name']} folds")
            return 0

        if action == "check":
            if self.current_bet > player["bet"]:
                raise ValueError("Cannot check while facing an outstanding bet.")
            self._log(f"{player['name']} checks")
            return 0

        if action == "call":
            needed = self.current_bet - player["bet"]
            if needed <= 0:
                self._log(f"{player['name']} checks")
                return 0
            actual = self._apply_bet(player_index, needed)
            self._log(f"{player['name']} calls ({actual})")
            return actual

        if action == "raise":
            if amount is None:
                raise ValueError("A raise amount is required.")
            if amount <= 0:
                raise ValueError("Raise amount must be positive.")
            # First call the current bet, then raise on top
            needed = self.current_bet - player["bet"]
            total = needed + amount
            actual = self._apply_bet(player_index, total)
            self._log(f"{player['name']} raises to {player['bet']}")
            return actual

        raise ValueError(f"Unsupported action: {action}")

    def run_betting_round(self, human_index, get_action_fn):
        """Run a full betting round. get_action_fn(game, player_index) returns action.

        Returns when all non-folded players have acted and bets are matched.
        """
        n = len(self.players)
        active_count = sum(1 for p in self.players if not p["folded"])
        if active_count <= 1:
            return

        # Track who still needs to act or re-act after a raise
        has_acted = [p["folded"] for p in self.players]
        # Start from the player after the one with the highest bet context
        start = self._next_seat(self.dealer_index, skip_folded=True)
        current = start

        while True:
            player = self.players[current]

            if not player["folded"] and not has_acted[current]:
                if current == human_index:
                    action_result = get_action_fn(self, current)
                else:
                    action_result = self._bot_action(current)

                old_bet = self.current_bet

                if isinstance(action_result, tuple):
                    self.place_bet(current, action_result[0], action_result[1])
                else:
                    self.place_bet(current, action_result)

                has_acted[current] = True

                # If a raise happened, everyone else needs to act again
                if self.current_bet > old_bet:
                    for i in range(n):
                        if i != current and not self.players[i]["folded"]:
                            has_acted[i] = False

            # Check: are we done?
            active_count = sum(1 for p in self.players if not p["folded"])
            if active_count <= 1:
                return

            all_acted = all(
                has_acted[i] or self.players[i]["folded"] for i in range(n)
            )
            all_matched = all(
                self.players[i]["bet"] == self.current_bet or self.players[i]["folded"]
                for i in range(n)
            )
            if all_acted and all_matched:
                return

            current = self._next_seat(current, skip_folded=True)

    def _bot_action(self, player_index):
        """Smarter bot decision-making."""
        player = self.players[player_index]
        if player["chips"] <= 0:
            return "fold"

        cost_to_call = self.current_bet - player["bet"]
        hand_strength = self._estimate_hand_strength(player_index)

        # Can check for free — never fold
        if cost_to_call == 0:
            if hand_strength >= 0.7:
                raise_amt = max(20, int(player["chips"] * 0.15))
                return ("raise", raise_amt)
            return "check"

        # Facing a bet
        pot_odds = cost_to_call / max(self.pot + cost_to_call, 1)

        if hand_strength >= 0.8:
            # Strong hand: raise
            raise_amt = max(20, int(player["chips"] * 0.2))
            return ("raise", raise_amt)
        elif hand_strength >= 0.4 or pot_odds < 0.3:
            # Decent hand or cheap to call
            return "call"
        elif cost_to_call <= player["chips"] * 0.1:
            # Very cheap to call relative to stack
            return "call"
        else:
            return "fold"

    def _estimate_hand_strength(self, player_index):
        """Rough hand strength estimate (0.0 to 1.0) for bot decision-making."""
        player = self.players[player_index]
        cards = player["hole_cards"] + self.community_cards

        if len(cards) < 2:
            return 0.5

        # Pre-flop: evaluate hole cards only
        if len(self.community_cards) == 0:
            c1, c2 = player["hole_cards"]
            r1, r2 = card_value(c1), card_value(c2)
            suited = c1[-1] == c2[-1]
            paired = r1 == r2

            strength = (r1 + r2) / 28.0  # Normalize by max (14+14)
            if paired:
                strength += 0.25
            if suited:
                strength += 0.08
            if abs(r1 - r2) <= 2 and not paired:
                strength += 0.05  # Connector bonus
            return min(strength, 1.0)

        # Post-flop: use actual hand evaluation
        score = evaluate_hand(cards)
        rank = score[0]
        # Map hand rank to approximate strength
        rank_strength = {
            0: 0.1, 1: 0.25, 2: 0.45, 3: 0.55,
            4: 0.65, 5: 0.7, 6: 0.75, 7: 0.85,
            8: 0.92, 9: 0.97, 10: 1.0,
        }
        return rank_strength.get(rank, 0.3)

    def bot_decision(self, player_index):
        """Legacy bot decision for backward compatibility."""
        player = self.players[player_index]
        if player["chips"] <= 0:
            return "fold"

        choices = ["check", "call", "raise", "fold"]
        if self.current_bet > 0:
            choices = ["call", "raise", "fold"]
        if self.current_bet == 0:
            choices = ["check", "raise", "fold"]
        return random.choice(choices)

    def deal_flop(self):
        self.deck.draw()  # Burn card
        self.community_cards.extend([self.deck.draw() for _ in range(3)])

    def deal_turn(self):
        self.deck.draw()  # Burn card
        self.community_cards.append(self.deck.draw())

    def deal_river(self):
        self.deck.draw()  # Burn card
        self.community_cards.append(self.deck.draw())

    def active_player_count(self):
        """Return the count of non-folded players."""
        return sum(1 for p in self.players if not p["folded"])

    def winner(self):
        if not self.players:
            raise ValueError("The game has no players.")

        eligible = [player for player in self.players if not player.get("folded", False)]
        if not eligible:
            raise ValueError("No players remain in the hand.")

        scored = []
        for idx, player in enumerate(self.players):
            if player.get("folded", False):
                continue
            cards = player["hole_cards"] + self.community_cards
            score = evaluate_hand(cards)
            scored.append({"name": player["name"], "score": score, "index": idx})

        scored.sort(key=lambda item: item["score"], reverse=True)

        winner = scored[0]
        # Award pot to winner
        self.players[winner["index"]]["chips"] += self.pot
        self._log(f"{winner['name']} wins {self.pot} chips!")
        pot_awarded = self.pot
        self.pot = 0

        return {**winner, "pot_awarded": pot_awarded}


def card_value(card):
    rank = card[:-1]
    if rank == "10":
        return 10
    return RANK_ORDER[rank]


def _straight_high(ranks):
    unique = sorted(set(ranks))
    if unique == [2, 3, 4, 5, 14]:
        return 5
    for idx in range(len(unique) - 4):
        window = unique[idx : idx + 5]
        if window == list(range(window[0], window[0] + 5)):
            return window[-1]
    return None


def _five_card_score(cards):
    ranks = sorted((card_value(card) for card in cards), reverse=True)
    counts = Counter(ranks)
    flush = len({card[-1] for card in cards}) == 1
    straight_high = _straight_high(ranks)

    if flush and ranks == [14, 13, 12, 11, 10]:
        return (10, 14)
    if flush and straight_high is not None:
        return (9, straight_high)

    if sorted(counts.values(), reverse=True) == [4, 1]:
        quad = max(rank for rank, count in counts.items() if count == 4)
        kicker = max(rank for rank, count in counts.items() if count == 1)
        return (8, quad, kicker)

    if sorted(counts.values(), reverse=True) == [3, 2]:
        triple = max(rank for rank, count in counts.items() if count == 3)
        pair = max(rank for rank, count in counts.items() if count == 2)
        return (7, triple, pair)

    if flush:
        return (6, *ranks)

    if straight_high is not None:
        return (5, straight_high)

    if sorted(counts.values(), reverse=True) == [3, 1, 1]:
        triple = max(rank for rank, count in counts.items() if count == 3)
        kickers = sorted((rank for rank, count in counts.items() if count == 1), reverse=True)
        return (4, triple, *kickers)

    if sorted(counts.values(), reverse=True) == [2, 2, 1]:
        pairs = sorted((rank for rank, count in counts.items() if count == 2), reverse=True)
        kicker = max(rank for rank, count in counts.items() if count == 1)
        return (3, *pairs, kicker)

    if sorted(counts.values(), reverse=True) == [2, 1, 1, 1]:
        pair = max(rank for rank, count in counts.items() if count == 2)
        kickers = sorted((rank for rank, count in counts.items() if count == 1), reverse=True)
        return (2, pair, *kickers)

    return (1, *ranks)


def evaluate_hand(cards):
    """Return the best five-card poker evaluation for the given hand."""
    if len(cards) < 5:
        ordered = sorted((card_value(card) for card in cards), reverse=True)
        return (0, *ordered)

    best_score = None
    for hand in combinations(cards, 5):
        score = _five_card_score(hand)
        if best_score is None or score > best_score:
            best_score = score
    return best_score


def compare_hands(hand_one, hand_two):
    score_one = evaluate_hand(hand_one)
    score_two = evaluate_hand(hand_two)

    if score_one > score_two:
        return 1
    if score_two > score_one:
        return -1
    return 0
