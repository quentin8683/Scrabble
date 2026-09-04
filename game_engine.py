"""
Moteur de jeu Scrabble — version "headless" (sans interface graphique).

Ce fichier remplace une ancienne version couplée à Tkinter (fenêtre,
simpledialog, messagebox), incompatible avec un serveur Flask sans
affichage. La logique de jeu (plateau, scoring, dictionnaire, règles
de placement) est conservée à l'identique ; seule l'interface change :
au lieu de dessiner des boutons et d'attendre des clics, chaque action
est une méthode appelée par le serveur avec un `player_index`, qui
renvoie (succès: bool, message/erreur: str).
"""

from board import Board, BOARD_SIZE
from player import Player
from tiles import TileBag, TILE_VALUES
from dictionary import dictionary


class ScrabbleGame:

    def __init__(self, player_names):
        self.board = Board()
        self.tile_bag = TileBag()

        self.players = [Player(name) for name in player_names]
        self.number_of_players = len(self.players)

        self.current_player = 0

        # Tuiles posées pendant le tour actuel (avant validation par /play)
        self.pending = []

        # Nombre de passes successives (pour détecter la fin de partie)
        self.consecutive_passes = 0

        self.game_over = False
        self.final_ranking = None

        self.distribute_tiles()

    # =========================================================
    # DISTRIBUTION
    # =========================================================

    def distribute_tiles(self):
        for player in self.players:
            player.rack = self.tile_bag.draw_multiple(7)

    def refill(self, player):
        while len(player.rack) < 7:
            tile = self.tile_bag.draw()
            if tile is None:
                break
            player.rack.append(tile)

    # =========================================================
    # ÉTAT (pour l'API /state)
    # =========================================================

    def _board_grid(self):
        return [
            [self.board.get(r, c) for c in range(BOARD_SIZE)]
            for r in range(BOARD_SIZE)
        ]

    def _multiplier_grid(self):
        return [
            [self.board.multiplier_at(r, c) for c in range(BOARD_SIZE)]
            for r in range(BOARD_SIZE)
        ]

    def private_state(self, player_index):
        """État du jeu du point de vue d'un joueur donné (son propre chevalet)."""
        if player_index is None or not (0 <= player_index < len(self.players)):
            return {"error": "Index de joueur invalide"}

        player = self.players[player_index]

        return {
            "board": self._board_grid(),
            "multiplier_grid": self._multiplier_grid(),
            "players": [
                {"name": p.name, "score": p.score}
                for p in self.players
            ],
            "current_player": self.current_player,
            "rack": player.rack,
            "pending": [
                {"row": p["row"], "col": p["col"], "letter": p["letter"]}
                for p in self.pending
            ],
            "remaining": self.tile_bag.remaining(),
            "game_over": self.game_over,
            "final_ranking": self.final_ranking,
        }

    # =========================================================
    # VALIDATION DU PLACEMENT
    # =========================================================

    def validate_placement(self):
        if not self.pending:
            return False, "Aucune lettre posée."

        positions = [(p["row"], p["col"]) for p in self.pending]

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
            positions_sorted = sorted(positions, key=lambda p: p[1])
            start, end = positions_sorted[0][1], positions_sorted[-1][1]

            for col in range(start, end + 1):
                if self.board.get(row, col) is None and (row, col) not in positions:
                    return False, "Le mot ne peut pas contenir de trou."
        else:
            col = next(iter(cols))
            positions_sorted = sorted(positions, key=lambda p: p[0])
            start, end = positions_sorted[0][0], positions_sorted[-1][0]

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

    # =========================================================
    # CONSTRUCTION DES MOTS
    # =========================================================

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

        while (
            self.board.inside(r - dr, c - dc)
            and self.get_letter(r - dr, c - dc) is not None
        ):
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

    def find_words(self):
        words = []

        for p in self.pending:
            r, c = p["row"], p["col"]

            word, positions = self.build_word(r, c, 0, 1)
            if len(word) >= 2:
                words.append(("horizontal", word, positions))

            word, positions = self.build_word(r, c, 1, 0)
            if len(word) >= 2:
                words.append(("vertical", word, positions))

        unique = []
        seen = set()
        for direction, word, positions in words:
            key = (direction, tuple(positions))
            if key not in seen:
                seen.add(key)
                unique.append((direction, word, positions))

        return unique

    # =========================================================
    # SCORE
    # =========================================================

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

    # =========================================================
    # ACTIONS (appelées par le serveur avec un player_index)
    # =========================================================

    def place(self, player_index, row, col, rack_index, joker_letter=None):
        if self.game_over:
            return False, "La partie est terminée."

        if player_index != self.current_player:
            return False, "Ce n'est pas votre tour."

        if row is None or col is None or rack_index is None:
            return False, "Paramètres de placement invalides."

        if not (0 <= row < BOARD_SIZE and 0 <= col < BOARD_SIZE):
            return False, "Case hors du plateau."

        if self.board.get(row, col) is not None:
            return False, "Case déjà occupée."

        if any(p["row"] == row and p["col"] == col for p in self.pending):
            return False, "Case déjà utilisée ce tour-ci."

        player = self.players[player_index]

        if rack_index < 0 or rack_index >= len(player.rack):
            return False, "Tuile invalide."

        if any(p["rack_index"] == rack_index for p in self.pending):
            return False, "Cette tuile est déjà posée ce tour-ci."

        tile = player.rack[rack_index]

        if tile == "?":
            if not joker_letter:
                return False, "Le joker nécessite une lettre."
            joker_letter = str(joker_letter).strip().upper()
            if len(joker_letter) != 1 or not joker_letter.isalpha():
                return False, "Lettre de joker invalide."
            placed_letter = joker_letter
        else:
            placed_letter = tile

        self.pending.append({
            "row": row,
            "col": col,
            "letter": placed_letter,
            "tile": tile,
            "rack_index": rack_index
        })

        return True, "Lettre placée."

    def cancel(self, player_index):
        if player_index != self.current_player:
            return False, "Ce n'est pas votre tour."

        self.pending.clear()
        return True, "Placement annulé."

    def play(self, player_index):
        if self.game_over:
            return False, "La partie est terminée."

        if player_index != self.current_player:
            return False, "Ce n'est pas votre tour."

        valid, error = self.validate_placement()
        if not valid:
            return False, error

        words = self.find_words()
        if not words:
            return False, "Aucun mot valide n'a été créé."

        for _, word, _ in words:
            if word not in dictionary:
                return False, f"« {word} » n'est pas autorisé."

        # Calcul des scores AVANT de vider self.pending
        # (score_word a besoin de self.pending pour les bonus/jokers)
        word_scores = []
        total_score = 0
        for _, word, positions in words:
            score = self.score_word(word, positions)
            word_scores.append((word, score))
            total_score += score

        if len(self.pending) == 7:
            total_score += 50

        player = self.players[player_index]

        positions = []
        for p in self.pending:
            self.board.set(p["row"], p["col"], p["letter"])
            positions.append((p["row"], p["col"]))

        self.board.consume_multipliers(positions)

        for p in sorted(self.pending, key=lambda x: x["rack_index"], reverse=True):
            index = p["rack_index"]
            if index < len(player.rack):
                player.rack.pop(index)

        player.add_score(total_score)
        self.pending.clear()
        self.refill(player)
        self.consecutive_passes = 0

        word_list = "\n".join(f"{word} : {score} pts" for word, score in word_scores)
        message = f"{word_list}\nTOTAL : +{total_score} points"

        if len(player.rack) == 0 and self.tile_bag.remaining() == 0:
            self._end_game()
            return True, f"{message}\n\n{self.final_ranking}"

        self.next_turn()
        return True, message

    def pass_turn(self, player_index):
        if self.game_over:
            return False, "La partie est terminée."

        if player_index != self.current_player:
            return False, "Ce n'est pas votre tour."

        if self.pending:
            self.pending.clear()

        self.consecutive_passes += 1

        # Règle simplifiée : deux tours par joueur sans jouer -> fin de partie
        if self.consecutive_passes >= (self.number_of_players * 2):
            self._end_game()
            return True, self.final_ranking

        self.next_turn()
        return True, "Tour passé."

    def exchange(self, player_index, indices):
        if self.game_over:
            return False, "La partie est terminée."

        if player_index != self.current_player:
            return False, "Ce n'est pas votre tour."

        if self.pending:
            return False, "Annule d'abord ton placement en cours."

        if self.tile_bag.remaining() < 1:
            return False, "Le sac est vide."

        if not indices:
            return False, "Aucune position fournie."

        try:
            indices = sorted({int(i) for i in indices}, reverse=True)
        except (TypeError, ValueError):
            return False, "Positions invalides."

        player = self.players[player_index]

        if any(i < 0 or i >= len(player.rack) for i in indices):
            return False, "Une position est invalide."

        if len(indices) > self.tile_bag.remaining():
            return False, "Pas assez de lettres dans le sac."

        old_tiles = [player.rack.pop(i) for i in indices]
        new_tiles = self.tile_bag.draw_multiple(len(old_tiles))
        player.rack.extend(new_tiles)
        self.tile_bag.put_back(old_tiles)

        self.consecutive_passes = 0
        self.next_turn()
        return True, "Lettres échangées."

    # =========================================================
    # TOUR SUIVANT / FIN DE PARTIE
    # =========================================================

    def next_turn(self):
        self.current_player += 1
        if self.current_player >= self.number_of_players:
            self.current_player = 0

    def _end_game(self):
        for player in self.players:
            penalty = sum(TILE_VALUES.get(tile, 0) for tile in player.rack)
            player.score -= penalty

        ranking = sorted(self.players, key=lambda p: p.score, reverse=True)

        lines = ["FIN DE PARTIE", ""]
        for i, player in enumerate(ranking):
            lines.append(f"{i + 1}. {player.name} : {player.score} points")

        self.game_over = True
        self.final_ranking = "\n".join(lines)
