from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import logging

# Configuration des logs pour le débogage
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import de votre moteur de jeu
try:
    from game_engine import ScrabbleGame as GameEngine
    logger.info("✅ GameEngine importé depuis game_engine.py")
except ImportError:
    try:
        from game import ScrabbleGame as GameEngine
        logger.info("✅ GameEngine importé depuis game.py")
    except ImportError:
        logger.error("❌ Impossible d'importer GameEngine")
        raise

app = Flask(__name__)
CORS(app)  # Permet aux clients de se connecter depuis n'importe où

# ============================================================
# ÉTAT DU JEU
# ============================================================

engine = None
players = []
game_started = False
max_players = 2  # Valeur par défaut

# ============================================================
# ENDPOINTS DE L'API
# ============================================================

@app.route('/')
def home():
    """Page d'accueil / statut du serveur"""
    return jsonify({
        "status": "Scrabble Server is running!",
        "players": players,
        "players_count": len(players),
        "game_started": game_started,
        "max_players": max_players
    })

@app.route('/status', methods=['GET'])
def get_status():
    """Retourne l'état détaillé du serveur"""
    return jsonify({
        "game_started": game_started,
        "players_count": len(players),
        "players": players,
        "max_players": max_players,
        "engine_initialized": engine is not None
    })

@app.route('/reset', methods=['POST'])
def reset_game():
    """Réinitialise complètement la partie"""
    global engine, players, game_started, max_players
    engine = None
    players = []
    game_started = False
    max_players = 2
    logger.info("🔄 Partie réinitialisée")
    return jsonify({
        "status": "reset",
        "message": "Partie réinitialisée avec succès"
    })

@app.route('/join', methods=['POST'])
def join_game():
    """Un joueur rejoint la partie"""
    global engine, players, game_started, max_players
    
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "Requête invalide : JSON attendu"}), 400
        
        name = data.get('name', 'Joueur').strip()
        if not name:
            name = "Joueur"
        
        # 🔥 Récupérer le nombre de joueurs depuis la requête
        max_players = data.get('max_players', 2)
        if max_players < 2:
            max_players = 2
        elif max_players > 4:
            max_players = 4
        
        logger.info(f"📥 Tentative de connexion : {name} (max {max_players} joueurs)")
        logger.info(f"   État actuel : {len(players)} joueurs, game_started={game_started}")
        
        # Vérifier si la partie est pleine
        if len(players) >= max_players:
            logger.warning(f"❌ Partie pleine : {len(players)}/{max_players} joueurs")
            return jsonify({"error": f"Partie complète ({max_players} joueurs maximum)"}), 400
        
        # Vérifier si le nom existe déjà
        if name in players:
            logger.warning(f"❌ Nom déjà pris : {name}")
            return jsonify({"error": f"Le nom '{name}' est déjà utilisé."}), 400
        
        # Ajouter le joueur
        player_index = len(players)
        players.append(name)
        logger.info(f"✅ Joueur ajouté : {name} (index {player_index})")
        
        # 🔥 Démarrer la partie SEULEMENT quand max_players est atteint
        if len(players) >= max_players and not game_started:
            try:
                engine = GameEngine(players)
                game_started = True
                logger.info(f"🎮 Partie démarrée avec {len(players)} joueurs : {players}")
            except Exception as e:
                logger.error(f"❌ Erreur lors du démarrage du jeu : {e}")
                players.pop()
                return jsonify({"error": f"Erreur de démarrage : {str(e)}"}), 500
        
        # Calculer le nombre de joueurs manquants
        waiting_for = max_players - len(players)
        
        return jsonify({
            "player_index": player_index,
            "game_started": game_started,
            "players_count": len(players),
            "max_players": max_players,
            "waiting_for": waiting_for,
            "message": f"Bienvenue {name} !",
            "waiting": len(players) < max_players
        })
        
    except Exception as e:
        logger.error(f"❌ Erreur dans /join : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/state', methods=['GET'])
def get_state():
    """Récupère l'état du jeu pour un joueur"""
    try:
        player_index = request.args.get('player_index', default=0, type=int)
        
        if not game_started or engine is None:
            return jsonify({
                "game_started": False,
                "waiting": True,
                "players_count": len(players),
                "max_players": max_players,
                "waiting_for": max_players - len(players),
                "players": [
                    {"name": p, "score": 0, "rack_count": 0}
                    for p in players
                ],
                "message": f"En attente de {max_players - len(players)} autre(s) joueur(s)..."
            })
        
        state = engine.private_state(player_index)
        state["game_started"] = True
        state["players_count"] = len(players)
        state["max_players"] = max_players
        return jsonify(state)
        
    except Exception as e:
        logger.error(f"❌ Erreur dans /state : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/place', methods=['POST'])
def place_tile():
    """Pose une tuile"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "JSON attendu"}), 400
        
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
            
    except Exception as e:
        logger.error(f"❌ Erreur dans /place : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/play', methods=['POST'])
def play_word():
    """Joue le mot"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "JSON attendu"}), 400
        
        player_index = data.get('player_index')
        
        if not game_started or engine is None:
            return jsonify({"error": "Partie pas encore commencée"}), 400
        
        success, result = engine.play(player_index)
        
        if success:
            return jsonify({"success": True, "result": result})
        else:
            return jsonify({"success": False, "error": result}), 400
            
    except Exception as e:
        logger.error(f"❌ Erreur dans /play : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/pass', methods=['POST'])
def pass_turn():
    """Passe son tour"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "JSON attendu"}), 400
        
        player_index = data.get('player_index')
        
        if not game_started or engine is None:
            return jsonify({"error": "Partie pas encore commencée"}), 400
        
        success, result = engine.pass_turn(player_index)
        
        if success:
            return jsonify({"success": True, "result": result})
        else:
            return jsonify({"success": False, "error": result}), 400
            
    except Exception as e:
        logger.error(f"❌ Erreur dans /pass : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/exchange', methods=['POST'])
def exchange_tiles():
    """Échange des tuiles"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "JSON attendu"}), 400
        
        player_index = data.get('player_index')
        indices = data.get('indices', [])
        
        if not game_started or engine is None:
            return jsonify({"error": "Partie pas encore commencée"}), 400
        
        success, result = engine.exchange(player_index, indices)
        
        if success:
            return jsonify({"success": True, "result": result})
        else:
            return jsonify({"success": False, "error": result}), 400
            
    except Exception as e:
        logger.error(f"❌ Erreur dans /exchange : {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/cancel', methods=['POST'])
def cancel_placement():
    """Annule le placement"""
    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "JSON attendu"}), 400
        
        player_index = data.get('player_index')
        
        if not game_started or engine is None:
            return jsonify({"error": "Partie pas encore commencée"}), 400
        
        success, result = engine.cancel(player_index)
        
        if success:
            return jsonify({"success": True, "message": result})
        else:
            return jsonify({"success": False, "error": result}), 400
            
    except Exception as e:
        logger.error(f"❌ Erreur dans /cancel : {e}")
        return jsonify({"error": str(e)}), 500

# ============================================================
# GESTION DES ERREURS GLOBALES
# ============================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint non trouvé"}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"❌ Erreur interne : {error}")
    return jsonify({"error": "Erreur interne du serveur"}), 500

# ============================================================
# DÉMARRAGE DU SERVEUR
# ============================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    logger.info(f"🚀 Démarrage du serveur sur le port {port}")
    logger.info(f"📂 Dictionnaire chargé")
    app.run(host="0.0.0.0", port=port, debug=False)
