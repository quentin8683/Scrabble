from flask import Flask, request, jsonify
from flask_cors import CORS
import os

# Importez votre moteur de jeu
# Si vous avez renommé game.py en game_engine.py
try:
    from game_engine import GameEngine
except ImportError:
    # Si vous avez gardé game.py
    from game import GameEngine

app = Flask(__name__)
CORS(app)  # Permet aux clients de se connecter depuis n'importe où

# État du jeu
engine = None
players = []
game_started = False

# ============================================================
# ENDPOINTS DE L'API
# ============================================================

@app.route('/')
def home():
    return jsonify({
        "status": "Scrabble Server is running!",
        "players": len(players),
        "game_started": game_started
    })

@app.route('/join', methods=['POST'])
def join_game():
    """Un joueur rejoint la partie"""
    global engine, players, game_started
    
    data = request.get_json()
    name = data.get('name', 'Joueur')
    
    if game_started:
        return jsonify({"error": "La partie a déjà commencé"}), 400
    
    if len(players) >= 4:
        return jsonify({"error": "Partie complète"}), 400
    
    player_index = len(players)
    players.append(name)
    
    # Démarrer la partie à 2 joueurs
    if len(players) >= 2 and not game_started:
        engine = GameEngine(players)
        game_started = True
    
    return jsonify({
        "player_index": player_index,
        "game_started": game_started,
        "message": f"Bienvenue {name} !"
    })

@app.route('/state', methods=['GET'])
def get_state():
    """Récupère l'état du jeu pour un joueur"""
    player_index = int(request.args.get('player_index', 0))
    
    if not game_started or engine is None:
        return jsonify({"error": "Partie pas encore commencée"}), 400
    
    state = engine.private_state(player_index)
    return jsonify(state)

@app.route('/place', methods=['POST'])
def place_tile():
    """Pose une tuile"""
    data = request.get_json()
    player_index = data.get('player_index')
    row = data.get('row')
    col = data.get('col')
    rack_index = data.get('rack_index')
    joker_letter = data.get('joker_letter')
    
    if not game_started or engine is None:
        return jsonify({"error": "Partie pas encore commencée"}), 400
    
    success, result = engine.place(
        player_index, row, col, rack_index, joker_letter
    )
    
    if success:
        return jsonify({"success": True, "message": result})
    else:
        return jsonify({"success": False, "error": result}), 400

@app.route('/play', methods=['POST'])
def play_word():
    """Joue le mot"""
    data = request.get_json()
    player_index = data.get('player_index')
    
    if not game_started or engine is None:
        return jsonify({"error": "Partie pas encore commencée"}), 400
    
    success, result = engine.play(player_index)
    
    if success:
        return jsonify({"success": True, "result": result})
    else:
        return jsonify({"success": False, "error": result}), 400

@app.route('/pass', methods=['POST'])
def pass_turn():
    """Passe son tour"""
    data = request.get_json()
    player_index = data.get('player_index')
    
    if not game_started or engine is None:
        return jsonify({"error": "Partie pas encore commencée"}), 400
    
    success, result = engine.pass_turn(player_index)
    
    if success:
        return jsonify({"success": True, "result": result})
    else:
        return jsonify({"success": False, "error": result}), 400

@app.route('/exchange', methods=['POST'])
def exchange_tiles():
    """Échange des tuiles"""
    data = request.get_json()
    player_index = data.get('player_index')
    indices = data.get('indices', [])
    
    if not game_started or engine is None:
        return jsonify({"error": "Partie pas encore commencée"}), 400
    
    success, result = engine.exchange(player_index, indices)
    
    if success:
        return jsonify({"success": True, "result": result})
    else:
        return jsonify({"success": False, "error": result}), 400

@app.route('/cancel', methods=['POST'])
def cancel_placement():
    """Annule le placement"""
    data = request.get_json()
    player_index = data.get('player_index')
    
    if not game_started or engine is None:
        return jsonify({"error": "Partie pas encore commencée"}), 400
    
    success, result = engine.cancel(player_index)
    
    if success:
        return jsonify({"success": True, "message": result})
    else:
        return jsonify({"success": False, "error": result}), 400

# ============================================================
# DÉMARRAGE DU SERVEUR
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port, debug=False)
