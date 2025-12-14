import random

# ----- Cards -----
class Card:
    def __init__(self, name, img):
        self.name = name
        self.img = img

class Defuse(Card):
    def __init__(self, img):
        super().__init__("Defuse", img)

class ExplodingKitten(Card):
    def __init__(self, img):
        super().__init__("Exploding Kitten", img)

class Attack(Card):
    def __init__(self, img):
        super().__init__("Attack", img)

class Skip(Card):
    def __init__(self, img):
        super().__init__("Skip", img)

class Favor(Card):
    def __init__(self, img):
        super().__init__("Favor", img)

# ----- Player -----
class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.is_alive = True

# ----- Deck -----
class Deck:
    def __init__(self):
        self.cards = []

    def shuffle(self):
        random.shuffle(self.cards)

    def draw(self):
        if self.cards:
            return self.cards.pop(0)
        return None

# ----- Game -----
class Game:
    def __init__(self, player_names):
        self.players = [Player(n) for n in player_names]
        self.active_index = 0
        self.messages = []
        self.deck = Deck()
        self.discard = Deck()
        self.setup_deck()
        self.deal_cards()
        self.add_message("Game started!")

    def setup_deck(self):
        # Add images for each card (card1.jpg .. card45.jpg)
        img_index = 1
        for _ in range(3):
            self.deck.cards.append(Attack(f"card{img_index}.jpg")); img_index+=1
            self.deck.cards.append(Skip(f"card{img_index}.jpg")); img_index+=1
            self.deck.cards.append(Favor(f"card{img_index}.jpg")); img_index+=1
        for _ in range(len(self.players)-1):
            self.deck.cards.append(ExplodingKitten(f"card{img_index}.jpg")); img_index+=1
        for _ in range(len(self.players)):
            self.deck.cards.append(Defuse(f"card{img_index}.jpg")); img_index+=1
        self.deck.shuffle()

    def deal_cards(self):
        for p in self.players:
            # 1 Defuse
            p.hand.append(Defuse(f"card{random.randint(1,45)}.jpg"))
            for _ in range(3):
                card = self.deck.draw()
                if card:
                    p.hand.append(card)

    def add_message(self, text):
        self.messages.append(text)

    def draw_card(self):
        player = self.players[self.active_index]
        card = self.deck.draw()
        if not card:
            self.add_message("Deck is empty!")
            return
        self.add_message(f"{player.name} draws {card.name}")
        player.hand.append(card)

    def next_player(self):
        alive = [p for p in self.players if p.is_alive]
        if len(alive) <= 1:
            return None
        while True:
            self.active_index = (self.active_index + 1) % len(self.players)
            if self.players[self.active_index].is_alive:
                break
        return self.players[self.active_index]
