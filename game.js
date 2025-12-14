const startBtn = document.getElementById('start-btn');
const playerNamesInput = document.getElementById('player-names');
const playersArea = document.getElementById('players-area');
const gameArea = document.getElementById('game-area');
const deckDiv = document.getElementById('deck');
const messages = document.getElementById('messages');
const discardPile = document.getElementById('discard-pile'); 

let players = [];
let currentPlayer = 0; // The index of the player whose turn it is

const AI_MOVE_DELAY = 1200; // 1.2 seconds per AI move

// --- EVENT LISTENERS ---

// Start game
startBtn.addEventListener('click', async () => {
    const name = playerNamesInput.value.trim();
    if(!name) { alert("Enter your name!"); return; }

    const setupArea = document.getElementById('setup-area');
    setupArea.classList.add('hidden'); 

    const res = await fetch("/start_game", {
        method: "POST",
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({players: name})
    });
    const data = await res.json();
    if(data.error){ alert(data.error); return; }

    players = data.players;
    currentPlayer = data.current_player;
    renderPlayers();
    gameArea.classList.remove('hidden');

    // If the AI starts, process its moves immediately
    if (data.moves && data.moves.length > 0) {
        currentPlayer = data.current_player; 
        await processMoves(data.moves); 
        renderPlayers(); 
    }
});

// Draw card
deckDiv.addEventListener('click', async ()=>{
    const player = players[currentPlayer];
    // Check deck 'clickable' class and if player is alive
    if(!player.is_human || !player.is_alive || !deckDiv.classList.contains('clickable')) return; 

    // Visually disable the deck temporarily
    deckDiv.classList.remove('clickable');
    
    const res = await fetch("/draw_card",{method:"POST"});
    const data = await res.json();

    if(!data.moves) {
        // Re-enable if the server failed
        deckDiv.classList.add('clickable');
        return; 
    }

    // Update global state BEFORE processing moves
    currentPlayer = data.current_player;
    
    // Process the sequence of moves (Human draw + any AI turns)
    await processMoves(data.moves);
    
    // Final render to show the correct player's turn light
    renderPlayers();
});

// --- CORE GAME LOGIC ---

// Play card
async function playCard(idx){
    const player = players[currentPlayer];
    if(!player.is_human || !player.is_alive) return;

    // Visually disable interaction while processing
    deckDiv.classList.remove('clickable');
    
    // Remove card from local data immediately for responsive UI
    player.hand.splice(idx, 1);
    renderPlayers(); // Rerender to show card removed from hand
    
    const res = await fetch("/play_card",{
        method:"POST",
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({card_index: idx})
    });
    const data = await res.json();

    if(!data.moves) {
        deckDiv.classList.add('clickable');
        return; 
    }
    
    // Update global state
    currentPlayer = data.current_player;

    // Process the sequence of moves (Human play + any AI turns)
    await processMoves(data.moves);
    
    // Final render
    renderPlayers();
}


// Process moves sequentially with delay
async function processMoves(moves){
    for(const move of moves){
        const playerIdx = players.findIndex(p => p.name === move.player);
        const isAI = playerIdx !== undefined && !players[playerIdx].is_human;

        // 1. Message update
        if(move.message) messages.innerText = move.message;

        // 2. State update based on move type
        if(move.type === "draw" || move.type === "ai_draw"){
            const p = players[playerIdx];
            
            // Update local data (Human hand or AI hand length)
            if (p.is_human && move.card) {
                p.hand.push(move.card);
            } else if (!p.is_human) {
                p.hand_length = (p.hand_length || 0) + 1;
            }
            
            // ANIMATION CALL: Card Draw (for both Human and AI)
            flyCardAnimation(playerIdx); 
            
            // Rerender to show the card in the hand (or update the AI count)
            renderPlayers(); 
        }
        
        if(move.type === "play" && move.card && move.card.image){
            // ANIMATION CALL: Card Play (Only for AI needs animation)
            if (isAI) {
                const handDiv = document.getElementById(`hand-${playerIdx}`);
                // Find and remove the *last* back-card element for the animation start point
                const backCards = handDiv.querySelectorAll('.back-card');
                const cardToRemove = backCards[backCards.length - 1]; 

                if (cardToRemove) {
                    playCardAnimation(cardToRemove, move.card.image);
                }
            }

            // State Update
            updateDiscardPile(move.card.image);
            messages.innerText = `${move.player} played ${move.card.name}`;
            
            // If the player is AI, decrement its hand length locally
            if (!players[playerIdx].is_human) {
                 players[playerIdx].hand_length = Math.max(0, players[playerIdx].hand_length - 1);
            }
        }

        // 3. Update player status or current player (if provided by the server)
        if (move.new_current_player !== undefined) {
             currentPlayer = move.new_current_player;
        }
        if (move.dead_player_index !== undefined) {
             players[move.dead_player_index].is_alive = false;
        }

        // 4. Delay only for AI moves for better visualization
        if (playerIdx !== undefined && !players[playerIdx].is_human) {
            await new Promise(r => setTimeout(r, AI_MOVE_DELAY));
        } else {
             // Small delay for human actions to allow animation to start
             await new Promise(r => setTimeout(r, 100)); 
        }
        
        renderPlayers(); 
    }
}


// --- HELPER FUNCTIONS ---

// Helper function to update the discard pile image
function updateDiscardPile(cardImage) {
    if (!discardPile) return;
    
    discardPile.innerHTML = '';
    const img = document.createElement('img');
    img.src = cardImage.startsWith('/') ? cardImage : `/static/${cardImage}`; 
    discardPile.appendChild(img);
}

// Render players and their hands (The core UI update function)
function renderPlayers(){
    playersArea.innerHTML = '';
    
    // Set deck clickable status based on whether it's the human's turn
    const humanPlayerIsCurrent = players[currentPlayer] && players[currentPlayer].is_human && players[currentPlayer].is_alive;
    if (humanPlayerIsCurrent) {
        deckDiv.classList.add('clickable');
    } else {
        deckDiv.classList.remove('clickable');
    }

    players.forEach((p, idx) => {
        const div = document.createElement('div');
        div.classList.add('player-card');
        
        if(idx === currentPlayer && p.is_alive) { 
            div.classList.add('current');
        }

        // FIX: Consolidated innerHTML to one line to avoid multi-line string literal issues
        div.innerHTML = `<h3>${p.name} ${!p.is_alive ? '(Dead)' : ''}</h3><div class="player-hand" id="hand-${idx}"></div>`;
        
        playersArea.appendChild(div);

        const handDiv = document.getElementById(`hand-${idx}`);
        handDiv.innerHTML = '';

        if(p.is_human){
            // Logic for calculating card spread
            const totalCards = p.hand.length;
            const cardWidth = 70; 
            const maxSpread = 400; 
            const totalSpread = Math.min(maxSpread, cardWidth * (totalCards - 1));
            const containerWidth = handDiv.offsetWidth || 450; 
            const startX = (containerWidth - totalSpread) / 2;

            p.hand.forEach((c, i) => {
                const img = document.createElement('img');
                img.src = `/static/${c.image}`;
                img.title = c.name;
                
                // Only allow playing cards if it's the human's turn AND they are alive
                if (idx === currentPlayer && p.is_alive) {
                    img.onclick = () => playCard(i);
                    img.classList.add('playable');
                } else {
                    img.style.cursor = 'default';
                }

                const left = startX + (i * (totalSpread / (totalCards - 1 || 1)));
                const top = Math.abs(i - (totalCards - 1)/2) * 5; 

                img.style.left = `${left}px`;
                img.style.top = `${top}px`;
                handDiv.appendChild(img);
            });
        } else {
            // AI hand
            handDiv.classList.add('ai-hand'); 
            for(let i = 0; i < p.hand_length; i++){ 
                const back = document.createElement('div'); 
                back.classList.add('back-card');
                handDiv.appendChild(back);
            }
        }
    });
}


// Card draw animation (flying card) - Used by both Human and AI
function flyCardAnimation(targetPlayerIdx){
    const handDiv = document.getElementById(`hand-${targetPlayerIdx}`);
    if(!handDiv) return;

    const flyingCard = document.createElement('div'); 
    flyingCard.classList.add('fly'); 
    // Uses backphoto.jpg for the card back image
    flyingCard.style.backgroundImage = `url("/static/images/backphoto.jpg")`;
    document.body.appendChild(flyingCard);

    const deckRect = deckDiv.getBoundingClientRect(); 
    const handRect = handDiv.getBoundingClientRect();

    // Set initial position (at the deck)
    flyingCard.style.left = deckRect.left + 'px';
    flyingCard.style.top = deckRect.top + 'px';

    // Calculate the target position (center of the player's hand card area)
    const targetLeft = handRect.left + handRect.width / 2 - 40; 
    const targetTop = handRect.top + handRect.height / 2; 

    // Trigger the transition after the element is attached
    setTimeout(()=>{
        flyingCard.style.left = targetLeft + 'px'; 
        flyingCard.style.top = targetTop + 'px';
        flyingCard.style.transform = 'rotate(10deg) scale(0.9)'; 
    }, 50);
    
    // Remove the element after the animation duration (700ms from CSS)
    setTimeout(()=>flyingCard.remove(), 700);
}

// Card Play Animation (Used by AI)
function playCardAnimation(sourceElement, finalCardImage) {
    const discardPileRect = discardPile.getBoundingClientRect();
    const sourceRect = sourceElement.getBoundingClientRect();

    // 1. Create the flying element
    const playingCard = document.createElement('div');
    playingCard.classList.add('fly');
    playingCard.style.backgroundImage = `url("/static/images/backphoto.jpg")`; 
    
    // 2. Set initial position (at the AI card position)
    playingCard.style.left = sourceRect.left + 'px';
    playingCard.style.top = sourceRect.top + 'px';
    document.body.appendChild(playingCard);

    // 3. Immediately remove the static element from the AI hand for state update
    // The sourceElement was already removed in processMoves before this call.
    // However, if the sourceElement is still a node, remove it here:
    if (sourceElement.parentNode) {
        sourceElement.remove();
    }
    
    // 4. Calculate the target position (center of the discard pile)
    const targetLeft = discardPileRect.left + discardPileRect.width / 2 - 40;
    const targetTop = discardPileRect.top + discardPileRect.height / 2 - 70;

    // 5. Start the animation
    setTimeout(() => {
        playingCard.style.left = targetLeft + 'px';
        playingCard.style.top = targetTop + 'px';
        playingCard.style.transform = 'rotate(360deg) scale(1.1)';

        // 6. Flip the card mid-flight 
        setTimeout(() => {
            playingCard.style.backgroundImage = `url("/static/${finalCardImage}")`;
            playingCard.style.transform = 'rotate(360deg) scale(1.1) rotateY(180deg)'; 
        }, 350); 
        
    }, 50);

    // 7. Remove element when finished
    setTimeout(() => playingCard.remove(), 700);
}