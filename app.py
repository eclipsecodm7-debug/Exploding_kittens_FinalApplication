from flask import Flask, render_template, request, jsonify
import random

app = Flask(__name__)

# ---------------- CARD DATA (Simplified for this file) ----------------
CARD_NAMES = {
    "Attack": 3, "Skip": 3, "Favor": 3,
    "See the Future": 3, "Shuffle": 3, "Nope": 5, "Defuse": 4 
}
CARD_IMAGE_PATHS = [f"images/card{i}.jpg" for i in range(1, 46)]

class Card:
    available_images = CARD_IMAGE_PATHS.copy()

    def __init__(self, name):
        self.name = name
        if not Card.available_images:
            Card.available_images = CARD_IMAGE_PATHS.copy()
        
        self.image = random.choice(Card.available_images)
        Card.available_images.remove(self.image)

    def to_dict(self):
        return {"name": self.name, "image": self.image}

# Define all card classes
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
class SeeTheFuture(Card):
    def __init__(self):
        super().__init__("See the Future")
class Shuffle(Card):
    def __init__(self):
        super().__init__("Shuffle")
class Nope(Card):
    def __init__(self):
        super().__init__("Nope")


# ---------------- PLAYER CLASS & GAME STATE ----------------
class Player:
    def __init__(self, name, is_human=True):
        self.name = name
        self.hand = []
        self.is_alive = True
        self.is_human = is_human

players = []
deck = []
current_player_idx = 0
game_started = False
turns_to_take = 1 
pending_action = None 

# ---------------- HELPERS ----------------
def get_next_player_index(start_idx):
    idx = start_idx
    count = 0
    max_count = len(players) * 2
    while True:
        idx = (idx + 1) % len(players)
        if players[idx].is_alive:
            return idx
        if count >= max_count:
            return -1
        count += 1

def change_turn():
    global current_player_idx, turns_to_take
    turns_to_take = max(0, turns_to_take - 1)
    if turns_to_take == 0:
        current_player_idx = get_next_player_index(current_player_idx)
        if current_player_idx != -1:
            turns_to_take = 1
    return current_player_idx

def check_win_condition():
    alive_players = [p for p in players if p.is_alive]
    if len(alive_players) == 1:
        winner = alive_players[0]
        return winner, {"type": "win", "player": winner.name, "message": f"🏆 {winner.name} wins the game! 🏆"}
    if len(alive_players) == 0:
        return None, {"type": "game_broken", "message": "Game over! No remaining players. Restarting is recommended."}
    return None, None


# ---------------- AI LOGIC ----------------
def process_ai_turns():
    moves = []
    max_iterations = len(players) * 5 
    count = 0
    
    while current_player_idx != -1 and players[current_player_idx].is_alive and not players[current_player_idx].is_human:
        if count >= max_iterations: 
            moves.append({"type": "error", "message": "AI turn sequence stalled."})
            break 
        count += 1
        
        ai = players[current_player_idx]
        is_turn_skipped_by_play = False
        
        # --- AI Card Playing Phase ---
        ai_played_card = True
        while ai_played_card and not is_turn_skipped_by_play:
            ai_played_card = False
            
            playables = [c for c in ai.hand if not isinstance(c, ExplodingKitten) and not isinstance(c, Defuse)]
            played_card = None
            
            # 1. See the Future
            see_future_cards = [c for c in playables if isinstance(c, SeeTheFuture)]
            if see_future_cards and (len(deck) < 5 or any(isinstance(c, Defuse) for c in ai.hand)):
                played_card = see_future_cards[0]
            
            # 2. Attack
            attack_cards = [c for c in playables if isinstance(c, Attack)]
            if not played_card and attack_cards:
                played_card = attack_cards[0]
            
            # 3. Shuffle
            shuffle_cards = [c for c in playables if isinstance(c, Shuffle)]
            if not played_card and shuffle_cards and random.random() < 0.2:
                played_card = shuffle_cards[0]
            
            # 4. Favor 
            favor_cards = [c for c in playables if isinstance(c, Favor)]
            if not played_card and favor_cards and len(ai.hand) < 4:
                played_card = favor_cards[0]
            
            if played_card:
                ai.hand.remove(played_card)
                ai_played_card = True
                
                moves.append({
                    "type": "ai_play",
                    "player": ai.name,
                    "card": played_card.to_dict(),
                    "message": f"{ai.name} played {played_card.name}"
                })
                
                # Execute Card Effect 
                if isinstance(played_card, Attack):
                    next_idx = get_next_player_index(current_player_idx)
                    global turns_to_take
                    turns_to_take += 2
                    is_turn_skipped_by_play = True
                    
                elif isinstance(played_card, Skip):
                    is_turn_skipped_by_play = True
                    
                elif isinstance(played_card, Shuffle):
                    random.shuffle(deck)
                    moves.append({"type": "shuffle_effect", "message": "The Deck was Shuffled!"})

                elif isinstance(played_card, SeeTheFuture):
                    top_three = [c.name for c in deck[:3]]
                    moves.append({"type": "seefuture_effect", "player": ai.name, "cards": top_three, "message": f"{ai.name} saw the top 3 cards."})
                    
                elif isinstance(played_card, Favor):
                    target_players = [p for p in players if p.name != ai.name and p.is_alive and p.hand]
                    if target_players:
                        target = random.choice(target_players)
                        stolen_card_idx = random.randint(0, len(target.hand) - 1)
                        stolen_card = target.hand.pop(stolen_card_idx)
                        ai.hand.append(stolen_card)
                        moves.append({"type": "favor_effect", "player": ai.name, "target": target.name, "message": f"{ai.name} stole a card from {target.name}."})


        # --- Draw Card Phase ---
        if turns_to_take > 0 and ai.is_alive and not is_turn_skipped_by_play: 
            
            if deck:
                card = deck.pop(0)
                
                if isinstance(card, ExplodingKitten):
                    defuse = next((c for c in ai.hand if isinstance(c, Defuse)), None)
                    if defuse:
                        ai.hand.remove(defuse)
                        deck.insert(random.randint(0, len(deck)), card) 
                        moves.append({"type": "ai_defuse", "player": ai.name, "message": f"{ai.name} drew Exploding Kitten but used Defuse!"})
                    else:
                        ai.is_alive = False
                        moves.append({"type": "ai_explode", "player": ai.name, "dead_player_index": players.index(ai), "message": f"{ai.name} drew Exploding Kitten and exploded! 💀"})
                else:
                    ai.hand.append(card)
                    moves.append({"type": "ai_draw", "player": ai.name, "card": {"name": card.name}, "message": f"{ai.name} drew a card."})
            else:
                moves.append({"type": "error", "message": "Deck is empty in AI draw phase."})
            
            # --- End of Turn ---
            change_turn()
            
            winner, win_move = check_win_condition()
            if win_move:
                moves.append(win_move)
                if winner or win_move["type"] == "game_broken":
                    break

    moves.append({"new_current_player": current_player_idx, "turns_to_take": turns_to_take})
    return moves


# ---------------- ROUTES ----------------
@app.route("/")
def index():
    # Assuming you have an index.html template
    return render_template("index.html")

@app.route("/get_game_state", methods=["GET"])
def get_game_state():
    frontend_players = []
    for p in players:
        frontend_players.append({
            "name":p.name,
            "is_human":p.is_human,
            "is_alive":p.is_alive,
            "hand": [c.to_dict() for c in p.hand] if p.is_human else [], 
            "hand_length": len(p.hand),
        })
        
    return jsonify({
        "players": frontend_players,
        "current_player": current_player_idx,
        "turns_to_take": turns_to_take,
        "pending_action": pending_action
    })

@app.route("/start_game", methods=["POST"])
def start_game():
    global players, deck, current_player_idx, game_started, turns_to_take, pending_action
    
    data = request.json
    name = data.get("players","").strip()
    if not name:
        return jsonify({"error":"Enter your name!"})

    # Reset game state
    players.clear()
    players.append(Player(name,is_human=True))
    players.append(Player("AI",is_human=False))

    deck.clear()
    pending_action = None 
    
    # Initialize Deck and handle Defuse cards
    all_cards = []
    for card_name, count in CARD_NAMES.items():
        CardClass = globals().get(card_name.replace(" ", ""))
        if CardClass:
            for _ in range(count):
                all_cards.append(CardClass())

    # Separate Defuse cards for guaranteed distribution
    defuse_cards = [c for c in all_cards if isinstance(c, Defuse)]
    other_cards = [c for c in all_cards if not isinstance(c, Defuse) and not isinstance(c, ExplodingKitten)]

    # Deal cards: 1 Defuse + 4 random cards
    for p in players:
        # Give one Defuse (Guaranteed)
        if defuse_cards:
            p.hand.append(defuse_cards.pop(0))
        
        # Give 4 random cards (from other_cards pool)
        for _ in range(4):
            if other_cards: p.hand.append(other_cards.pop(random.randrange(len(other_cards))))

    # Recombine remaining non-Defuse cards into the deck
    deck.extend(other_cards)

    # Add Exploding Kittens (N-1 where N is player count)
    for _ in range(len(players)-1): 
        deck.append(ExplodingKitten())
        
    random.shuffle(deck)

    current_player_idx = random.randint(0, len(players) - 1)
    turns_to_take = 1
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

    moves = []
    if not players[current_player_idx].is_human:
        moves.extend(process_ai_turns())
    else:
        moves.append({"message": f"{players[current_player_idx].name}'s turn (Draw 1)"})
        moves.append({"new_current_player": current_player_idx, "turns_to_take": turns_to_take})
    
    final_player_idx = moves[-1].get("new_current_player", current_player_idx)
    
    # Update hand lengths before sending
    for p_fe in frontend_players:
        p_real = next((p for p in players if p.name == p_fe['name']), None)
        if p_real:
             p_fe['hand_length'] = len(p_real.hand)

    return jsonify({"players":frontend_players,"current_player":final_player_idx, "moves": moves})

@app.route("/draw_card", methods=["POST"])
def draw_card():
    global current_player_idx
    if not game_started or players[current_player_idx].is_human == False or players[current_player_idx].is_alive == False:
        return jsonify({"error":"It's not your turn or game not started"})

    player = players[current_player_idx]
    moves = []

    if not deck:
        moves.append({"message": "Deck is empty! Game should have ended already."})
    else:
        card = deck.pop(0) 
        
        if isinstance(card, ExplodingKitten):
            defuse = next((c for c in player.hand if isinstance(c, Defuse)),None)
            if defuse:
                player.hand.remove(defuse)
                
                # Player must choose where to put the kitten (for now, random)
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
                "message":f"{player.name} drew {card.name}. Turns left: {turns_to_take}"
            })

    # 1. Move to next player after drawing (or exploding)
    change_turn()

    # 2. Check for winner
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
    human_player_hand = [c.to_dict() for c in player.hand] if player.is_alive else []
    
    return jsonify({"moves":moves,"current_player":final_player_idx, "human_hand": human_player_hand})


@app.route("/play_card", methods=["POST"])
def play_card():
    global current_player_idx, turns_to_take, pending_action
    data = request.json
    idx = data.get("card_index")
    target_name = data.get("target_player_name") 

    player = players[current_player_idx]
    
    if idx is None or not isinstance(idx, int) or idx < 0 or idx >= len(player.hand) or not player.is_human or not player.is_alive:
        return jsonify({"error":"Invalid card index or player state"})

    card = player.hand.pop(idx) 
    
    human_play_move = {
        "type": "play",
        "card": card.to_dict(),
        "player": player.name, 
        "message": f"{player.name} played {card.name}"
    }
    
    moves = [human_play_move]
    turn_ends = False 

    # --- Favor Card Logic Modification ---
    if isinstance(card, Favor):
        target = next((p for p in players if p.name == target_name and p.is_alive and p.hand), None)
        
        if not target:
            moves.append({"message": f"Favor failed: {target_name} is not a valid target or has no cards."})
            turn_ends = False 
        else:
            target_hand_data = [c.to_dict() for c in target.hand]
            
            # HALT the game and enter PENDING_ACTION state
            pending_action = {
                "type": "favor_select",
                "player_making_favor": player.name, 
                "target_name": target.name, 
                "target_hand": target_hand_data, 
            }
            
            moves.append({"type": "pending_action", "details": pending_action})
            
            # Return immediately, waiting for resolve_favor
            return jsonify({
                "moves": moves,
                "current_player": current_player_idx, 
                "turns_to_take": turns_to_take,
                "human_hand": [c.to_dict() for c in player.hand], 
                "pending_action": pending_action
            })
            
    # --- Other Card Logic ---
    elif isinstance(card, Skip):
        change_turn()
        turn_ends = True
        
    elif isinstance(card, Attack):
        next_idx = get_next_player_index(current_player_idx)
        if players[next_idx].is_alive:
            turns_to_take += 2 
        change_turn()
        turn_ends = True

    elif isinstance(card, Shuffle):
        random.shuffle(deck)
        moves.append({"type": "shuffle_effect", "message": "The Deck was Shuffled!"})
        turn_ends = False
        
    elif isinstance(card, SeeTheFuture):
        top_three = [c.name for c in deck[:3]]
        moves.append({"type": "seefuture_effect", "player": player.name, "cards": top_three, "message": f"You saw the top 3 cards: {', '.join(top_three)}."})
        turn_ends = False

    elif isinstance(card, Defuse) or isinstance(card, ExplodingKitten):
        player.hand.append(card)
        return jsonify({"error": f"Cannot play {card.name} in this phase."})

    # Process AI moves if the turn ended (Skip or Attack)
    if turn_ends:
        winner, win_move = check_win_condition()
        if win_move:
            moves.append(win_move)
            winner_found = winner or win_move["type"] == "game_broken"
        else:
            winner_found = False

        if not winner_found:
            ai_moves = process_ai_turns()
            moves.extend(ai_moves)
            
    # Return the final state
    final_player_idx = moves[-1].get("new_current_player", current_player_idx)
    final_turns_to_take = moves[-1].get("turns_to_take", turns_to_take)
    human_player_hand = [c.to_dict() for c in player.hand]
    
    return jsonify({
        "moves": moves,
        "current_player": final_player_idx,
        "turns_to_take": final_turns_to_take,
        "human_hand": human_player_hand,
        "pending_action": pending_action
    })


# ---------------- NEW FAVOR RESOLUTION ROUTE ----------------
@app.route("/resolve_favor", methods=["POST"])
def resolve_favor():
    global pending_action, current_player_idx, turns_to_take
    data = request.json
    selected_card_name = data.get("card_name")

    if not pending_action or pending_action.get('type') != 'favor_select':
        return jsonify({"error": "No Favor action is pending."})
    
    player_making_favor = next((p for p in players if p.name == pending_action['player_making_favor']), None)
    target_player = next((p for p in players if p.name == pending_action['target_name']), None)

    if not player_making_favor or not target_player:
        pending_action = None
        return jsonify({"error": "Invalid player state for Favor resolution."})

    moves = []
    stolen_card = None
    
    # 1. Find and steal the selected card from the target player's hand
    for i, card in enumerate(target_player.hand):
        if card.name == selected_card_name:
            stolen_card = target_player.hand.pop(i)
            player_making_favor.hand.append(stolen_card)
            break

    pending_action = None # Clear the pending state
    
    if stolen_card:
        moves.append({
            "type": "favor_resolved",
            "player": player_making_favor.name,
            "target": target_player.name,
            "card_name": stolen_card.name,
            "message": f"{player_making_favor.name} successfully stole {stolen_card.name} from {target_player.name}."
        })
    else:
        moves.append({"type": "error", "message": "Failed to find selected card in target's hand."})

    # Favor does not end the turn; player must still draw. No turn change or AI processing needed here.
    final_player_idx = current_player_idx 
    final_turns_to_take = turns_to_take 
    
    human_player_hand = [c.to_dict() for c in player_making_favor.hand]
    
    return jsonify({
        "moves": moves,
        "current_player": final_player_idx,
        "turns_to_take": final_turns_to_take,
        "human_hand": human_player_hand,
        "pending_action": pending_action
    })


if __name__=="__main__":
    # Ensure this runs the server for testing
    app.run(debug=True)
