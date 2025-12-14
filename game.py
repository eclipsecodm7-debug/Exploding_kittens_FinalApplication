from player import Player
from deck import Deck
from cards import Defuse, ExplodingKitten, Attack, Skip, Favor

class Game:
    def __init__(self):
        self.players = []
        self.deck = Deck()
        self.discard = Deck()
        self.active_index = 0
        self.messages = []

    def add_players(self, names):
        for name in names:
            self.players.append(Player(name))

    def setup_deck(self):
        # Basic cards
        for _ in range(3):
            self.deck.add_card(Attack())
            self.deck.add_card(Skip())
            self.deck.add_card(Favor())
        # Exploding Kittens
        for _ in range(len(self.players)-1):
            self.deck.add_card(ExplodingKitten())
        # Defuse cards
        for _ in range(len(self.players)):
            self.deck.add_card(Defuse())
        self.deck.shuffle()

    def deal_cards(self):
        for p in self.players:
            p.hand.append(Defuse())  # Each player gets one Defuse
            for _ in range(3):
                card = self.deck.draw()
                if card:
                    p.hand.append(card)

    def draw_card(self, player):
        card = self.deck.draw()
        if card:
            self.messages.append(f"{player.name} draws {card.name}")
            if card.name == "Exploding Kitten":
                # Check for Defuse
                has_defuse = None
                for c in player.hand:
                    if c.name == "Defuse":
                        has_defuse = c
                        break
                if has_defuse:
                    player.hand.remove(has_defuse)
                    self.discard.add_card(has_defuse)
                    self.deck.add_card(card)
                    self.deck.shuffle()
                    self.messages.append(f"{player.name} used Defuse to avoid explosion!")
                else:
                    player.is_alive = False
                    self.messages.append(f"{player.name} exploded!")
            else:
                player.hand.append(card)