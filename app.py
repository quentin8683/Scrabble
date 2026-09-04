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
players = []  # Chaque entrée est un nom (str), ou None si le joueur est parti
game_started = False
target_max_players = None  # Défini par le premier joueur qui rejoint (l'hôte)


def active_players():
    """Liste des joueurs encore présents (ignore les emplacements libérés)."""
    return [p for p in players if p is not None]


# ============================================================
# ENDPOINTS DE L'API
# ============================================================

@app.route('/')
def home():
    """Page d'accueil / statut du serveur"""
    return jsonify({
        "status": "Scrabble Server is running!",
        "players": active_players(),
        "players_count": len(active_players()),
        "game_started": game_started,
        "max_players": target_max_players or 4,
        "configured": target_max_players is not None
    })


@app.route('/status', methods=['GET'])
def get_status():
    """Retourne l'état détaillé du serveur"""
    return jsonify({
        "game_started": game_started,
        "players_count": len(active_players()),
        "players": active_players(),
        "max_players": target_max_players or 4,
        "configured": target_max_players is not None,
        "engine_initialized": engine is not None
    })


@app.route('/leave', methods=['POST'])
def leave_game():
    """Un joueur quitte la partie (fermeture de la fenêtre)."""
    global players, game_started, target_max_players

    try:
        data = request.get_json()
        if data is None:
            return jsonify({"error": "JSON attendu"}), 400

        player_index = data.get('player_index')
        if (
            player_index is None
            or not (0 <= player_index < len(players))
            or players[player_index] is None
        ):
            return jsonify({"error": "Index de joueur invalide"}), 400

        if game_started:
            # On ne peut pas retirer un joueur en cours de partie sans
            # décaler tous les player_index et casser le moteur de jeu.
            logger.warning(
                f"⚠️ {players[player_index]} a fermé sa fenêtre en cours de partie "
                f"(index {player_index}) — non retiré pour ne pas casser la partie."
            )
            return jsonify({
                "success": False,
                "error": "La partie est déjà commencée : ce joueur ne peut pas être "
                         "retiré proprement. Utilisez /reset si la partie doit être "
                         "annulée."
            }), 400

        # Partie pas encore commencée : on libère l'emplacement (on ne fait
        # PAS de pop(), pour ne pas décaler les player_index des joueurs
        # déjà connectés à des indices supérieurs).
        removed_name = players[player_index]
        players[player_index] = None
        logger.info(f"👋 {removed_name} a quitté la salle d'attente (slot {player_index} libéré)")

        if not active_players():
            # Plus personne en attente : on réinitialise complètement
            players = []
            target_max_players = None
            logger.info("🔄 Salle d'attente vide, configuration réinitialisée")

        return jsonify({
            "success": True,
            "message": f"{removed_name} a quitté la partie.",
            "players_count": len(active_players())
        })

    except Exception as e:
        logger.error(f"❌ Erreur dans /leave : {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/reset', methods=['POST'])
def reset_game():
    """Réinitialise complètement la partie"""
    global engine, players, game_started, target_max_players
    engine = None
    players = []
    game_started = False
    target_max_players = None
    logger.info("🔄 Partie réinitialisée")
    return jsonify({
        "status": "reset",
        "message": "Partie réinitialisée avec succès"
    })


@app.route('/join', methods=['POST'])
def join_game():
    """Un joueur rejoint la partie"""
    global engine, players, game_started, target_max_players

    try:
        # Récupérer les données
        data = request.get_json()
        if data is None:
            logger.warning("⚠️ Requête /join sans JSON")
            return jsonify({"error": "Requête invalide : JSON attendu"}), 400

        name = data.get('name', 'Joueur').strip()
        if not name:
            name = "Joueur"

        requested_max_players = data.get('max_players', 4)
        try:
            requested_max_players = int(requested_max_players)
        except (TypeError, ValueError):
            requested_max_players = 4
        requested_max_players = max(2, min(4, requested_max_players))

        # Le premier joueur (l'hôte) fixe le nombre de joueurs de la partie
        if target_max_players is None:
            target_max_players = requested_max_players
            logger.info(f"🎯 Partie configurée pour {target_max_players} joueurs par {name}")

        logger.info(f"📥 Tentative de connexion : {name}")
        logger.info(f"   État actuel : {len(active_players())} joueurs, game_started={game_started}, cible={target_max_players}")

        # Vérifier si la partie est pleine (on ne compte que les joueurs actifs)
        if len(active_players()) >= target_max_players:
            logger.warning(f"❌ Partie pleine : {len(active_players())}/{target_max_players} joueurs")
            return jsonify({"error": f"Partie complète ({target_max_players} joueurs maximum)"}), 400

        # Vérifier si le nom existe déjà (parmi les joueurs actifs)
        if name in active_players():
            logger.warning(f"❌ Nom déjà pris : {name}")
            return jsonify({"error": f"Le nom '{name}' est déjà utilisé."}), 400

        # Ajouter le joueur : on réutilise un emplacement libéré (None) s'il y
        # en a un, plutôt que d'ajouter systématiquement à la fin. Cela évite
        # de décaler les player_index des autres joueurs déjà connectés.
        if None in players:
            player_index = players.index(None)
            players[player_index] = name
        else:
            player_index = len(players)
            players.append(name)
        logger.info(f"✅ Joueur ajouté : {name} (index {player_index})")

        # Démarrer la partie uniquement quand le nombre de joueurs voulu est atteint
        if len(active_players()) >= target_max_players and not game_started:
            try:
                # players[:target_max_players] ne contient plus aucun None à
                # cet instant précis, puisque c'est justement le dernier
                # emplacement qui vient d'être comblé.
                engine = GameEngine(players[:target_max_players])
                game_started = True
                logger.info(f"🎮 Partie démarrée avec {len(active_players())} joueurs : {active_players()}")
            except Exception as e:
                logger.error(f"❌ Erreur lors du démarrage du jeu : {e}")
                # Annuler l'ajout du joueur en cas d'erreur
                players[player_index] = None
                return jsonify({"error": f"Erreur de démarrage : {str(e)}"}), 500

        return jsonify({
            "player_index": player_index,
            "game_started": game_started,
            "players_count": len(active_players()),
            "max_players": target_max_players,
            "message": f"Bienvenue {name} !",
            "waiting": len(active_players()) < target_max_players
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
                "players_count": len(active_players()),
                "message": "En attente d'autres joueurs..."
            })

        state = engine.private_state(player_index)
        state["game_started"] = True
        state["players_count"] = len(active_players())
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
