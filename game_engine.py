from board import Board, BOARD_SIZE
from player import Player
from tiles import TileBag, TILE_VALUES
from dictionary import dictionary


class ScrabbleGame:
    """
    Version serveur de ScrabbleGame - Sans interface graphique
    Uniquement la logique métier
    """

    def __init__(self, players):
        """
        Initialise le jeu avec une liste de joueurs
        
        Args:
            players (list): Liste des noms des joueurs
        """
        self.number_of_players = len(players)
        
        self.board = Board()
        self.tile_bag = TileBag()
        
        # Créer les objets Player
        self.players = [
            Player(name) 
            for name in players
        ]
        
        self.current_player = 0
        self.pending = []  # Tuiles posées temporairement
        self.consecutive_passes = 0
        self.selected_index = None
        
        # Distribuer les tuiles
        for player in self.players:
            player.rack = self.tile_bag.draw_multiple(7)

    # ============================================================
    # ACCÈS À L'ÉTAT
    # ============================================================

    def private_state(self, player_index):
        """
        Retourne l'état du jeu pour un joueur spécifique
        """
        return {
            "board": self.board.grid,
            "used_multipliers": [
                list(position) 
                for position in self.board.used_multipliers
            ],
            "players": [
                {
                    "name": player.name,
                    "score": player.score,
                    "rack_count": len(player.rack)
                }
                for player in self.players
            ],
            "current_player": self.current_player,
            "remaining": self.tile_bag.remaining(),
            "pending": [
                {
                    "row": p["row"],
                    "col": p["col"],
                    "letter": p["letter"]
                }
                for p in self.pending
            ],
            "rack": list(self.players[player_index].rack)
        }

    # ============================================================
    # LETTRES / MOTS
    # ============================================================

    def get_letter(self, row, col):
        for p in self.pending:
            if p["row"] == row and p["col"] == col:
                return p["letter"]
        
        value = self.board.get(row, col)
        if value is None:
            return None
        if isinstance(value, tuple):
            return value[0]
        return value

    def build_word(self, row, col, dr, dc):
        r, c = row, col
        
        while (self.board.inside(r - dr, c - dc) and 
               self.get_letter(r - dr, c - dc) is not None):
            r -= dr
            c -= dc
        
        letters = []
        positions = []
        
        while self.board.inside(r, c):
            letter = self.get_letter(r, c)
            if letter is None:
                break
            letters.append(letter)
            positions.append((r, c))
            r += dr
            c += dc
        
        return "".join(letters), positions

    # ============================================================
    # VALIDATION DU PLACEMENT
    # ============================================================

    def validate_placement(self):
        if not self.pending:
            return False, "Aucune lettre posée."
        
        positions = [(p["row"], p["col"]) for p in self.pending]
        
        # Une seule lettre
        if len(positions) == 1:
            r, c = positions[0]
            if self.board.is_empty():
                if (r, c) != (7, 7):
                    return False, "Le premier mot doit passer par le centre."
            else:
                connected = any(
                    self.board.get(nr, nc) is not None
                    for nr, nc in self.board.neighbours(r, c)
                )
                if not connected:
                    return False, "Le mot doit être relié au plateau."
            return True, ""
        
        rows = {p[0] for p in positions}
        cols = {p[1] for p in positions}
        
        if len(rows) != 1 and len(cols) != 1:
            return False, "Les lettres doivent être alignées."
        
        horizontal = len(rows) == 1
        
        if horizontal:
            row = next(iter(rows))
            sorted_positions = sorted(positions, key=lambda p: p[1])
            start = sorted_positions[0][1]
            end = sorted_positions[-1][1]
            
            for col in range(start, end + 1):
                if self.board.get(row, col) is None and (row, col) not in positions:
                    return False, "Le mot ne peut pas contenir de trou."
        else:
            col = next(iter(cols))
            sorted_positions = sorted(positions, key=lambda p: p[0])
            start = sorted_positions[0][0]
            end = sorted_positions[-1][0]
            
            for row in range(start, end + 1):
                if self.board.get(row, col) is None and (row, col) not in positions:
                    return False, "Le mot ne peut pas contenir de trou."
        
        if self.board.is_empty():
            if (7, 7) not in positions:
                return False, "Le premier mot doit passer par la case centrale."
        else:
            connected = False
            for r, c in positions:
                for nr, nc in self.board.neighbours(r, c):
                    if self.board.get(nr, nc) is not None:
                        connected = True
                        break
                if connected:
                    break
            if not connected:
                return False, "Le nouveau mot doit être connecté au plateau."
        
        return True, ""

    # ============================================================
    # DETECTION DES MOTS
    # ============================================================

    def find_words(self):
        words = []
        seen = set()
        
        for p in self.pending:
            r, c = p["row"], p["col"]
            
            # Horizontal
            word, positions = self.build_word(r, c, 0, 1)
            if len(word) >= 2:
                key = ("horizontal", tuple(positions))
                if key not in seen:
                    seen.add(key)
                    words.append(("horizontal", word, positions))
            
            # Vertical
            word, positions = self.build_word(r, c, 1, 0)
            if len(word) >= 2:
                key = ("vertical", tuple(positions))
                if key not in seen:
                    seen.add(key)
                    words.append(("vertical", word, positions))
        
        return words

    # ============================================================
    # SCORE
    # ============================================================

    def score_word(self, word, positions):
        total = 0
        word_multiplier = 1
        
        for letter, (r, c) in zip(word, positions):
            value = TILE_VALUES.get(letter, 0)
            
            pending_tile = next(
                (p for p in self.pending if p["row"] == r and p["col"] == c),
                None
            )
            
            if pending_tile is not None:
                multiplier = self.board.multiplier_at(r, c)
                if multiplier == "DL":
                    value *= 2
                elif multiplier == "TL":
                    value *= 3
                elif multiplier == "DW":
                    word_multiplier *= 2
                elif multiplier == "TW":
                    word_multiplier *= 3
                if pending_tile["tile"] == "?":
                    value = 0
            
            total += value
        
        return total * word_multiplier

    # ============================================================
    # ACTIONS DU JOUEUR
    # ============================================================

    def place(self, player_index, row, col, rack_index, joker_letter=None):
        # Vérification du tour
        if player_index != self.current_player:
            return False, "Ce n'est pas votre tour."
        
        # Vérification de la case
        if not self.board.inside(row, col):
            return False, "Case invalide."
        
        if self.board.get(row, col) is not None:
            return False, "Cette case est déjà occupée."
        
        # Vérification doublon temporaire
        for p in self.pending:
            if p["row"] == row and p["col"] == col:
                return False, "Cette case est déjà sélectionnée."
        
        player = self.players[player_index]
        
        # Vérification du chevalet
        if rack_index < 0 or rack_index >= len(player.rack):
            return False, "Tuile invalide."
        
        tile = player.rack[rack_index]
        
        # Joker
        if tile == "?":
            if not joker_letter or len(joker_letter) != 1 or not joker_letter.isalpha():
                return False, "Le joker doit représenter une lettre."
            letter = joker_letter.upper()
        else:
            letter = tile
        
        # Placement temporaire
        self.pending.append({
            "row": row,
            "col": col,
            "letter": letter,
            "tile": tile,
            "rack_index": rack_index
        })
        
        return True, ""

    def cancel(self, player_index):
        if player_index != self.current_player:
            return False, "Ce n'est pas votre tour."
        
        self.pending.clear()
        return True, ""

    def play(self, player_index):
        if player_index != self.current_player:
            return False, "Ce n'est pas votre tour."
        
        # Validation
        valid, error = self.validate_placement()
        if not valid:
            return False, error
        
        # Recherche des mots
        words = self.find_words()
        if not words:
            return False, "Aucun mot valide n'a été créé."
        
        # Vérification dictionnaire
        for _, word, _ in words:
            if word not in dictionary:
                return False, f"« {word} » n'est pas autorisé."
        
        # Calcul du score
        total_score = 0
        for _, word, positions in words:
            total_score += self.score_word(word, positions)
        
        # Scrabble
        if len(self.pending) == 7:
            total_score += 50
        
        player = self.players[player_index]
        
        # Validation définitive
        positions = []
        for p in self.pending:
            self.board.set(p["row"], p["col"], p["letter"])
            positions.append((p["row"], p["col"]))
        
        self.board.consume_multipliers(positions)
        
        # Retirer les tuiles du chevalet
        for p in sorted(self.pending, key=lambda x: x["rack_index"], reverse=True):
            player.rack.pop(p["rack_index"])
        
        player.add_score(total_score)
        self.pending.clear()
        
        # Remplir le chevalet
        while len(player.rack) < 7:
            tile = self.tile_bag.draw()
            if tile is None:
                break
            player.rack.append(tile)
        
        self.consecutive_passes = 0
        
        result = {
            "score": total_score,
            "words": [word for _, word, _ in words]
        }
        
        # Fin de partie
        if len(player.rack) == 0 and self.tile_bag.remaining() == 0:
            result["game_over"] = self.finish()
            return True, result
        
        self.next_turn()
        return True, result

    def pass_turn(self, player_index):
        if player_index != self.current_player:
            return False, "Ce n'est pas votre tour."
        
        self.pending.clear()
        self.consecutive_passes += 1
        
        if self.consecutive_passes >= len(self.players) * 2:
            return True, {"game_over": self.finish()}
        
        self.next_turn()
        return True, {}

    def exchange(self, player_index, indices):
        if player_index != self.current_player:
            return False, "Ce n'est pas votre tour."
        
        if self.pending:
            return False, "Annulez d'abord votre placement."
        
        if not indices:
            return False, "Aucune tuile sélectionnée."
        
        if self.tile_bag.remaining() < len(indices):
            return False, "Pas assez de lettres dans le sac."
        
        player = self.players[player_index]
        
        indices = sorted(set(indices), reverse=True)
        
        if any(i < 0 or i >= len(player.rack) for i in indices):
            return False, "Position de tuile invalide."
        
        old_tiles = [player.rack[i] for i in indices]
        
        for index in indices:
            player.rack.pop(index)
        
        new_tiles = self.tile_bag.draw_multiple(len(old_tiles))
        player.rack.extend(new_tiles)
        self.tile_bag.put_back(old_tiles)
        
        self.consecutive_passes = 0
        self.next_turn()
        
        return True, {}

    def next_turn(self):
        self.current_player += 1
        if self.current_player >= len(self.players):
            self.current_player = 0

    def finish(self):
        # Retirer les points des lettres restantes
        for player in self.players:
            penalty = sum(TILE_VALUES[tile] for tile in player.rack)
            player.score -= penalty
        
        ranking = sorted(
            [
                {"name": player.name, "score": player.score}
                for player in self.players
            ],
            key=lambda p: p["score"],
            reverse=True
        )
        
        return ranking
