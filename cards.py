class Card:
    def __init__(self, name, image):
        self.name = name
        self.image = image

class Attack(Card):
    def __init__(self):
        super().__init__("Attack", "card5.jpg")

class Skip(Card):
    def __init__(self):
        super().__init__("Skip", "card39.jpg")

class Favor(Card):
    def __init__(self):
        super().__init__("Favor", "card19.jpg")

class Defuse(Card):
    def __init__(self):
        super().__init__("Defuse", "card14.jpg")

class ExplodingKitten(Card):
    def __init__(self):
        super().__init__("Exploding Kitten", "card18.jpg")
