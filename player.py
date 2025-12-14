class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.is_alive = True

    def show_hand(self):
        return ", ".join(f"{c.name}" for c in self.hand)

    def play_card(self, index):
        if 0 <= index < len(self.hand):
            return self.hand.pop(index)
        return None
