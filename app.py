from flask import Flask, render_template, request, jsonify
import random

app = Flask(__name__)

# ---------------- CARD CLASSES ----------------
# Use a simple counter for images since we only have 46 total
CARD_IMAGE_PATHS = [f"images/card{i}.jpg" for i in range(1, 46)]

class Card:
    available_images = CARD_IMAGE_PATHS.copy()

    def __init__(self, name):
        self.name = name
        # Cycle images if we run out (for simplicity)
        if not Card.available_images:
            Card.available_images = CARD_IMAGE_PATHS.copy()
        
        # Select and remove the image to ensure uniqueness for a while
        self.image = random.choice(Card.available_images)
        Card.available_images.remove(self.image)

    def to_dict(self):
        """Converts card object to a dict for JSON transfer."""
        return {"name": self.name, "image": self.image}

class Defuse(Card):
    def __init__(self):
        super().__init__("Defuse")

class ExplodingKitten(Card):
    def __init__(self):
        super().__init__("Exploding Kitten")

class Attack(Card):
    def __init__(self):
        super().__init__("Attack")

class Skip(Card):
    def __init__(self):
        super().__init__("Skip")

class Favor(Card):
    def __init__(self):
        super().__init__("Favor")

# ---------------- PLAYER CLASS ----------------
class Player:
    def __init__(self, name, is_human=True):
        self.name = name
        self.hand = []
        self.is_alive = True
        self.is_human = is_human

# ---------------- GAME STATE ----------------
players = []
deck = []
current_player_idx = 0
game_started = False

# ---------------- HELPERS ----------------
def next_turn():
    """Cycles the current_player_idx to the next ALIVE player."""
    global current_player_idx
    
    alive_indices = [i for i, p in enumerate(players) if p.is_alive]
    
    if len(alive_indices) <= 1:
        # Game over state or only one player left
        current_player_idx = alive_indices[0] if alive_indices else -1
        return current_player_idx
    
    # Use the current index as a starting point for search, not the original turn holder
    start_index = current_player_idx
    
    # We must start checking from the index *after* the current one.
    check_index = start_index

    # Loop a maximum of len(players) times
    for _ in range(len(players)):
        # Move to the next physical index (wrapping around)
        check_index = (check_index + 1) % len(players)
        
        # Check if the player at this new index is alive
        if players[check_index].is_alive:
            current_player_idx = check_index
            return current_player_idx
        
        # Safety break if we looped through everyone without finding an alive player
        if check_index == start_index:
             break

    # If the loop finishes without finding an alive player (should be caught by len(alive_indices) <= 1 above, but this is a safety net)
    current_player_idx = -1
    return current_player_idx


def check_win_condition():
    """Checks if only one player is alive (Last player standing wins)."""
    alive_players = [p for p in players if p.is_alive]
    
    if len(alive_players) == 1:
        winner = alive_players[0]
        return winner, {
            "type": "win",
            "player": winner.name,
            "message": f"🏆 {winner.name} wins the game! 🏆",
        }
    # NEW CHECK: If no one is left (shouldn't happen, but acts as a failsafe)
    if len(alive_players) == 0:
        return None, {
            "type": "game_broken",
            "message": "Game over! No remaining players. Restarting is recommended.",
        }
        
    return None, None

# ---------------- AI LOGIC ----------------
def process_ai_turns():
    """Process AI moves until it's human's turn, game ends, or a winner is declared."""
    moves = []
    
    # Loop while the current player is an AI and is alive
    while current_player_idx != -1 and players[current_player_idx].is_alive and not players[current_player_idx].is_human:
        
        ai = players[current_player_idx]
        human_players = [p for p in players if p.is_human and p.is_alive]

        # --- Decide card to play (AI Logic) ---
        played_card = None
        skip_cards = [c for c in ai.hand if isinstance(c, Skip)]
        
        # Priority 1: Skip if Exploding Kitten is next
        if skip_cards and any(isinstance(c, ExplodingKitten) for c in deck[:1]):
            played_card = skip_cards[0]
        
        # Priority 2: Attack/Favor
        elif human_players:
            attack_cards = [c for c in ai.hand if isinstance(c, Attack)]
            favor_cards = [c for c in ai.hand if isinstance(c, Favor)]
            
            if attack_cards and any(len(p.hand) < 3 for p in human_players): 
                played_card = attack_cards[0]
            elif favor_cards and any(len(p.hand) > 4 for p in human_players): 
                played_card = favor_cards[0]
            
        # Priority 3: Play a random playable card
        if not played_card:
            playables = [c for c in ai.hand if not isinstance(c, ExplodingKitten) and not isinstance(c, Defuse)]
            if playables:
                played_card = random.choice(playables)
        
        # Execute play card (optional)
        if played_card:
            ai.hand.remove(played_card)
            moves.append({
                "type":"play",
                "player":ai.name,
                "card":played_card.to_dict()
            })

        # --- Draw card (Mandatory action) ---
        if deck:
            card = deck.pop()
            
            if isinstance(card, ExplodingKitten):
                defuse = next((c for c in ai.hand if isinstance(c, Defuse)), None)
                if defuse:
                    ai.hand.remove(defuse)
                    # Reinsert the Kitten randomly
                    deck.insert(random.randint(0, len(deck)), card) 
                    moves.append({
                        "type": "ai_defuse",
                        "player": ai.name,
                        "message": f"{ai.name} drew Exploding Kitten but used Defuse!"
                    })
                else:
                    ai.is_alive = False
                    # Notify the frontend which player index is now dead
                    moves.append({
                        "type": "ai_explode",
                        "player": ai.name,
                        "dead_player_index": players.index(ai),
                        "message": f"{ai.name} drew Exploding Kitten and exploded! 💀"
                    })
            else:
                ai.hand.append(card)
                moves.append({
                    "type": "ai_draw",
                    "player": ai.name,
                    # Minimal data for AI draw to trigger animation/count update
                    "card": {"name": card.name}
                })
        
        # After the AI's turn is complete, move to the next player
        next_turn()
        
        # Check for winner after a player dies or turn changes
        winner, win_move = check_win_condition()
        if win_move:
            moves.append(win_move)
            if winner or win_move["type"] == "game_broken":
                break 

    # Send the index of the next player (or -1 if game over)
    moves.append({"new_current_player": current_player_idx})
    return moves

# ---------------- ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start_game", methods=["POST"])
def start_game():
    global players, deck, current_player_idx, game_started
    data = request.json
    name = data.get("players","").strip()
    if not name:
        return jsonify({"error":"Enter your name!"})

    # Reset game state
    players.clear()
    players.append(Player(name,is_human=True))
    players.append(Player("AI",is_human=False))

    deck.clear()
    # Initialize Deck (Simplified)
    for _ in range(3):
        deck.extend([Attack(),Skip(),Favor()])
    for _ in range(len(players)-1): # One less Kitten than players
        deck.append(ExplodingKitten())
    for _ in range(len(players)): # One Defuse per player
        deck.append(Defuse())
    random.shuffle(deck)

    # Deal cards: 1 Defuse + 4 random
    for p in players:
        # Find a Defuse card from the shuffled deck
        defuse_card = next((c for c in deck if isinstance(c, Defuse)), None)
        if defuse_card:
             deck.remove(defuse_card)
             p.hand.append(defuse_card)
        
        for _ in range(4):
            if deck: p.hand.append(deck.pop())

    current_player_idx = 0
    game_started = True

    frontend_players = []
    for p in players:
        frontend_players.append({
            "name":p.name,
            "is_human":p.is_human,
            "is_alive":p.is_alive,
            "hand": [c.to_dict() for c in p.hand] if p.is_human else [],
            "hand_length": len(p.hand),
        })

    moves = process_ai_turns()
    
    final_player_idx = moves[-1].get("new_current_player", current_player_idx)

    return jsonify({"players":frontend_players,"current_player":final_player_idx, "moves": moves})

@app.route("/draw_card", methods=["POST"])
def draw_card():
    global current_player_idx
    # Check if the player is human before proceeding
    if not game_started or players[current_player_idx].is_human == False:
        return jsonify({"error":"It's not your turn or game not started"})

    player = players[current_player_idx]
    moves = []

    if not deck:
        moves.append({"message": "Deck is empty! Game should have ended already."})
    else:
        card = deck.pop()
        
        if isinstance(card, ExplodingKitten):
            defuse = next((c for c in player.hand if isinstance(c, Defuse)),None)
            if defuse:
                player.hand.remove(defuse)
                deck.insert(random.randint(0,len(deck)),card)
                moves.append({
                    "type":"draw",
                    "player": player.name,
                    "card": card.to_dict(), 
                    "message":f"{player.name} drew Exploding Kitten but used Defuse!"
                })
            else:
                player.is_alive=False
                moves.append({
                    "type":"draw",
                    "player": player.name,
                    "dead_player_index": current_player_idx,
                    "message":f"{player.name} drew Exploding Kitten and exploded! 💀"
                })
        else:
            player.hand.append(card)
            moves.append({
                "type":"draw",
                "player": player.name,
                "card": card.to_dict(),
                "message":f"{player.name} drew {card.name}"
            })

    # 1. Move to next player after drawing (or exploding)
    next_turn()

    # 2. Check for winner immediately after human's action
    winner, win_move = check_win_condition()
    if win_move:
        moves.append(win_move)
        winner_found = winner or win_move["type"] == "game_broken"
    else:
        winner_found = False

    # 3. Process AI moves only if no winner was found yet
    if not winner_found:
        ai_moves = process_ai_turns()
        moves.extend(ai_moves)

    final_player_idx = moves[-1].get("new_current_player", current_player_idx)
    return jsonify({"moves":moves,"current_player":final_player_idx})

@app.route("/play_card", methods=["POST"])
def play_card():
    global current_player_idx
    data = request.json
    idx = data.get("card_index")
    player = players[current_player_idx]
    
    # Validation
    if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(player.hand) or not player.is_human or not player.is_alive:
        return jsonify({"error":"Invalid card index or player state"})

    card = player.hand.pop(idx)
    
    # Human play move
    human_play_move = {
        "type": "play",
        "card": card.to_dict(),
        "player": player.name, 
        "message": f"{player.name} played {card.name}"
    }
    
    moves = [human_play_move]

    winner_found = False

    if isinstance(card, Skip):
        # Skip ends the turn immediately. The human player does NOT draw.
        next_turn()
        
        # Check for winner immediately after a skip moves the turn
        winner, win_move = check_win_condition()
        if win_move:
            moves.append(win_move)
            winner_found = winner or win_move["type"] == "game_broken"

    # Process AI moves only if no winner was found yet
    if not winner_found:
        ai_moves = process_ai_turns()
        moves.extend(ai_moves)

    final_player_idx = moves[-1].get("new_current_player", current_player_idx)
    
    return jsonify({
        "moves": moves,
        "current_player": final_player_idx
    })

if __name__=="__main__":
    app.run(debug=True)