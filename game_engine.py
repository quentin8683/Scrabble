import tkinter as tk
from tkinter import messagebox, simpledialog

from board import Board, BOARD_SIZE
from player import Player
from tiles import TileBag, TILE_VALUES
from dictionary import dictionary


class ScrabbleGame:

    def __init__(self, root, number_of_players):

        self.root = root
        self.number_of_players = number_of_players

        self.board = Board()
        self.tile_bag = TileBag()

        self.players = []

        for i in range(number_of_players):

            name = simpledialog.askstring(
                "Nom du joueur",
                f"Nom du joueur {i + 1} :",
                parent=root
            )

            if not name:
                name = f"Joueur {i + 1}"

            self.players.append(
                Player(name)
            )

        self.current_player = 0

        # Tuiles posées pendant le tour actuel
        self.pending = []

        # Nombre de passes successives
        self.consecutive_passes = 0

        self.create_interface()

        self.distribute_tiles()

        self.update_interface()

    # =========================================================
    # INTERFACE
    # =========================================================

    def create_interface(self):

        self.root.title("Scrabble")
        self.root.geometry("1250x850")
        self.root.configure(bg="#1f2937")

        self.main_frame = tk.Frame(
            self.root,
            bg="#1f2937"
        )

        self.main_frame.pack(
            fill="both",
            expand=True
        )

        # --------------------------
        # PLATEAU
        # --------------------------

        self.board_frame = tk.Frame(
            self.main_frame,
            bg="#1f2937"
        )

        self.board_frame.pack(
            side="left",
            padx=20,
            pady=20
        )

        self.cells = []

        for row in range(BOARD_SIZE):

            row_cells = []

            for col in range(BOARD_SIZE):

                button = tk.Button(
                    self.board_frame,
                    text="",
                    width=3,
                    height=1,
                    font=("Arial", 10, "bold"),
                    command=lambda r=row, c=col:
                    self.board_click(r, c)
                )

                button.grid(
                    row=row,
                    column=col,
                    padx=1,
                    pady=1
                )

                row_cells.append(button)

            self.cells.append(row_cells)

        # --------------------------
        # PANNEAU
        # --------------------------

        self.side_frame = tk.Frame(
            self.main_frame,
            bg="#111827"
        )

        self.side_frame.pack(
            side="right",
            fill="y",
            padx=10,
            pady=20
        )

        tk.Label(
            self.side_frame,
            text="SCRABBLE",
            font=("Arial", 26, "bold"),
            fg="white",
            bg="#111827"
        ).pack(pady=15)

        self.turn_label = tk.Label(
            self.side_frame,
            text="",
            font=("Arial", 16, "bold"),
            fg="#60a5fa",
            bg="#111827"
        )

        self.turn_label.pack(pady=10)

        self.score_label = tk.Label(
            self.side_frame,
            text="",
            font=("Arial", 13),
            fg="white",
            bg="#111827",
            justify="left"
        )

        self.score_label.pack(pady=10)

        tk.Label(
            self.side_frame,
            text="Chevalet",
            font=("Arial", 15, "bold"),
            fg="white",
            bg="#111827"
        ).pack(pady=5)

        self.rack_frame = tk.Frame(
            self.side_frame,
            bg="#111827"
        )

        self.rack_frame.pack()

        self.play_button = tk.Button(
            self.side_frame,
            text="JOUER LE MOT",
            font=("Arial", 12, "bold"),
            bg="#16a34a",
            fg="white",
            command=self.play_word
        )

        self.play_button.pack(
            fill="x",
            padx=25,
            pady=8
        )

        self.cancel_button = tk.Button(
            self.side_frame,
            text="Annuler",
            command=self.cancel_pending
        )

        self.cancel_button.pack(
            fill="x",
            padx=25,
            pady=4
        )

        self.pass_button = tk.Button(
            self.side_frame,
            text="Passer",
            command=self.pass_turn
        )

        self.pass_button.pack(
            fill="x",
            padx=25,
            pady=4
        )

        self.exchange_button = tk.Button(
            self.side_frame,
            text="Échanger",
            command=self.exchange_tiles
        )

        self.exchange_button.pack(
            fill="x",
            padx=25,
            pady=4
        )

        self.remaining_label = tk.Label(
            self.side_frame,
            text="",
            fg="#9ca3af",
            bg="#111827"
        )

        self.remaining_label.pack(pady=15)

    # =========================================================
    # DISTRIBUTION
    # =========================================================

    def distribute_tiles(self):

        for player in self.players:

            player.rack = (
                self.tile_bag.draw_multiple(7)
            )

    def refill(self, player):

        while len(player.rack) < 7:

            tile = self.tile_bag.draw()

            if tile is None:
                break

            player.rack.append(tile)

    # =========================================================
    # AFFICHAGE
    # =========================================================

    def update_interface(self):

        self.update_board()
        self.update_rack()
        self.update_scores()

        player = self.players[
            self.current_player
        ]

        self.turn_label.config(
            text=f"Tour de {player.name}"
        )

        self.remaining_label.config(
            text=(
                f"Lettres dans le sac : "
                f"{self.tile_bag.remaining()}"
            )
        )

    def update_board(self):

        for r in range(BOARD_SIZE):

            for c in range(BOARD_SIZE):

                button = self.cells[r][c]

                letter = self.board.get(r, c)

                if letter is not None:

                    # Un joker est affiché comme sa lettre choisie
                    display = (
                        letter[0]
                        if isinstance(letter, tuple)
                        else letter
                    )

                    button.config(
                        text=display,
                        bg="#f59e0b",
                        fg="black"
                    )

                    continue

                multiplier = self.board.multiplier_at(r, c)

                button.config(
                    text=self.multiplier_text(
                        multiplier
                    ),
                    bg=self.multiplier_color(
                        multiplier
                    ),
                    fg="black"
                )

        # Lettres posées temporairement
        for position in self.pending:

            r = position["row"]
            c = position["col"]
            letter = position["letter"]

            self.cells[r][c].config(
                text=letter,
                bg="#22c55e",
                fg="black"
            )

    def multiplier_text(self, multiplier):

        return {
            "TW": "M×3",
            "DW": "M×2",
            "TL": "L×3",
            "DL": "L×2"
        }.get(multiplier, "")

    def multiplier_color(self, multiplier):

        return {
            "TW": "#ef4444",
            "DW": "#fca5a5",
            "TL": "#3b82f6",
            "DL": "#93c5fd"
        }.get(
            multiplier,
            "#e5e7eb"
        )

    def update_scores(self):

        text = ""

        for player in self.players:

            text += (
                f"{player.name} : "
                f"{player.score}\n"
            )

        self.score_label.config(
            text=text
        )

    def update_rack(self):

        for widget in self.rack_frame.winfo_children():
            widget.destroy()

        player = self.players[
            self.current_player
        ]

        for index, tile in enumerate(player.rack):

            value = TILE_VALUES[tile]

            text = (
                "?"
                if tile == "?"
                else tile
            )

            button = tk.Button(
                self.rack_frame,
                text=f"{text}\n{value}",
                width=4,
                height=2,
                font=("Arial", 11, "bold"),
                command=lambda i=index:
                self.select_tile(i)
            )

            button.grid(
                row=0,
                column=index,
                padx=2
            )

    # =========================================================
    # SELECTION
    # =========================================================

    def select_tile(self, index):

        player = self.players[
            self.current_player
        ]

        if index >= len(player.rack):
            return

        # Une seule tuile sélectionnée
        self.selected_index = index

    # =========================================================
    # PLACEMENT
    # =========================================================

    def board_click(self, row, col):

        player = self.players[
            self.current_player
        ]

        if self.board.get(row, col) is not None:
            return

        if not hasattr(self, "selected_index"):
            return

        index = self.selected_index

        if index >= len(player.rack):
            return

        tile = player.rack[index]

        # Pour le joker :
        # on demande quelle lettre il représente.
        if tile == "?":

            letter = simpledialog.askstring(
                "Joker",
                "Quelle lettre représente le joker ?",
                parent=self.root
            )

            if not letter:
                return

            letter = letter.upper()

            if len(letter) != 1 or not letter.isalpha():
                messagebox.showerror(
                    "Joker",
                    "Entre une seule lettre."
                )
                return

            placed_letter = letter

        else:

            placed_letter = tile

        # Vérifier qu'on ne pose pas deux fois au même endroit
        for item in self.pending:

            if (
                item["row"] == row
                and
                item["col"] == col
            ):
                return

        self.pending.append({
            "row": row,
            "col": col,
            "letter": placed_letter,
            "tile": tile,
            "rack_index": index
        })

        del self.selected_index

        self.update_interface()

    # =========================================================
    # ANNULATION
    # =========================================================

    def cancel_pending(self):

        self.pending.clear()

        if hasattr(self, "selected_index"):
            del self.selected_index

        self.update_interface()

    # =========================================================
    # VALIDATION DU PLACEMENT
    # =========================================================

    def validate_placement(self):

        if not self.pending:
            return False, "Aucune lettre posée."

        positions = [
            (p["row"], p["col"])
            for p in self.pending
        ]

        # Une seule lettre
        if len(positions) == 1:

            r, c = positions[0]

            if self.board.is_empty():

                if (r, c) != (7, 7):
                    return (
                        False,
                        "Le premier mot doit passer par le centre."
                    )

            else:

                connected = any(
                    self.board.get(nr, nc) is not None
                    for nr, nc in
                    self.board.neighbours(r, c)
                )

                if not connected:
                    return (
                        False,
                        "Le mot doit être relié au plateau."
                    )

            return True, ""

        rows = {p[0] for p in positions}
        cols = {p[1] for p in positions}

        if len(rows) != 1 and len(cols) != 1:

            return (
                False,
                "Les lettres doivent être alignées."
            )

        horizontal = len(rows) == 1

        if horizontal:

            row = next(iter(rows))

            positions_sorted = sorted(
                positions,
                key=lambda p: p[1]
            )

            start = positions_sorted[0][1]
            end = positions_sorted[-1][1]

            for col in range(start, end + 1):

                if self.board.get(row, col) is None:

                    if (row, col) not in positions:
                        return (
                            False,
                            "Le mot ne peut pas contenir de trou."
                        )

        else:

            col = next(iter(cols))

            positions_sorted = sorted(
                positions,
                key=lambda p: p[0]
            )

            start = positions_sorted[0][0]
            end = positions_sorted[-1][0]

            for row in range(start, end + 1):

                if self.board.get(row, col) is None:

                    if (row, col) not in positions:
                        return (
                            False,
                            "Le mot ne peut pas contenir de trou."
                        )

        # Premier coup : doit toucher le centre
        if self.board.is_empty():

            if (7, 7) not in positions:

                return (
                    False,
                    "Le premier mot doit passer par la case centrale."
                )

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

                return (
                    False,
                    "Le nouveau mot doit être connecté au plateau."
                )

        return True, ""

    # =========================================================
    # CONSTRUCTION DES MOTS
    # =========================================================

    def get_letter(self, row, col):

        # Tuile temporaire
        for p in self.pending:

            if (
                p["row"] == row
                and
                p["col"] == col
            ):
                return p["letter"]

        # Tuile déjà sur le plateau
        value = self.board.get(row, col)

        if value is None:
            return None

        if isinstance(value, tuple):
            return value[0]

        return value

    def build_word(self, row, col, dr, dc):

        # Remonter jusqu'au début du mot
        r = row
        c = col

        while (
            self.board.inside(r - dr, c - dc)
            and
            self.get_letter(r - dr, c - dc) is not None
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

        # Pour chaque nouvelle tuile
        for p in self.pending:

            r = p["row"]
            c = p["col"]

            # Horizontal
            word, positions = self.build_word(
                r, c, 0, 1
            )

            if len(word) >= 2:
                words.append(
                    ("horizontal", word, positions)
                )

            # Vertical
            word, positions = self.build_word(
                r, c, 1, 0
            )

            if len(word) >= 2:
                words.append(
                    ("vertical", word, positions)
                )

        # Supprimer doublons
        unique = []

        seen = set()

        for direction, word, positions in words:

            key = (
                direction,
                tuple(positions)
            )

            if key not in seen:

                seen.add(key)

                unique.append(
                    (direction, word, positions)
                )

        return unique

    # =========================================================
    # SCORE
    # =========================================================

    def score_word(self, word, positions):

        total = 0
        word_multiplier = 1

        for letter, (r, c) in zip(
            word,
            positions
        ):

            value = TILE_VALUES.get(
                letter,
                0
            )

            # Le bonus ne s'applique que
            # si la case vient d'être jouée.
            pending_tile = next(
                (
                    p
                    for p in self.pending
                    if p["row"] == r
                    and p["col"] == c
                ),
                None
            )

            if pending_tile is not None:

                multiplier = (
                    self.board.multiplier_at(
                        r, c
                    )
                )

                if multiplier == "DL":
                    value *= 2

                elif multiplier == "TL":
                    value *= 3

                elif multiplier == "DW":
                    word_multiplier *= 2

                elif multiplier == "TW":
                    word_multiplier *= 3

                # Joker = 0
                if pending_tile["tile"] == "?":
                    value = 0

            total += value

        return total * word_multiplier

    # =========================================================
    # JOUER
    # =========================================================

    def play_word(self):

        valid, error = self.validate_placement()

        if not valid:

            messagebox.showerror(
                "Placement invalide",
                error
            )

            return

        words = self.find_words()

        # Aucun mot détecté
        if not words:

            messagebox.showerror(
                "Mot invalide",
                "Aucun mot valide n'a été créé."
            )

            return

        # Vérification dictionnaire
        for _, word, _ in words:

            if word not in dictionary:

                messagebox.showerror(
                    "Mot invalide",
                    f"« {word} » n'est pas autorisé."
                )

                return

        # -------------------------
        # CALCUL
        # -------------------------

        total_score = 0

        for _, word, positions in words:

            total_score += self.score_word(
                word,
                positions
            )

        # Scrabble = 7 tuiles posées
        if len(self.pending) == 7:

            total_score += 50

        player = self.players[
            self.current_player
        ]

        # -------------------------
        # VALIDATION DÉFINITIVE
        # -------------------------

        positions = []

        for p in self.pending:

            r = p["row"]
            c = p["col"]

            self.board.set(
                r,
                c,
                p["letter"]
            )

            positions.append(
                (r, c)
            )

        # Les bonus viennent d'être consommés
        self.board.consume_multipliers(
            positions
        )

        # Retirer les tuiles du chevalet
        for p in sorted(
            self.pending,
            key=lambda x: x["rack_index"],
            reverse=True
        ):

            index = p["rack_index"]

            if index < len(player.rack):

                player.rack.pop(index)

        player.add_score(
            total_score
        )

        self.pending.clear()

        self.refill(player)

        self.consecutive_passes = 0

        word_list = "\n".join(
            f"{word} : "
            f"{self.score_word(word, positions)} pts"
            for _, word, positions in words
        )

        messagebox.showinfo(
            "Mot joué",
            f"{word_list}\n\n"
            f"TOTAL : +{total_score} points"
        )

        # Fin de partie
        if (
            len(player.rack) == 0
            and
            self.tile_bag.remaining() == 0
        ):

            self.end_game()
            return

        self.next_turn()

    # =========================================================
    # PASSER
    # =========================================================

    def pass_turn(self):

        if self.pending:

            self.cancel_pending()

        self.consecutive_passes += 1

        # Règle simplifiée :
        # deux tours par joueur sans jouer
        if self.consecutive_passes >= (
            self.number_of_players * 2
        ):

            self.end_game()

            return

        self.next_turn()

    # =========================================================
    # ÉCHANGE
    # =========================================================

    def exchange_tiles(self):

        if self.pending:

            messagebox.showwarning(
                "Échange",
                "Annule d'abord ton placement."
            )

            return

        if self.tile_bag.remaining() < 1:

            messagebox.showwarning(
                "Échange",
                "Le sac est vide."
            )

            return

        player = self.players[
            self.current_player
        ]

        choice = simpledialog.askstring(
            "Échanger",
            "Indique les positions des lettres à échanger\n"
            "Exemple : 1 3 5",
            parent=self.root
        )

        if not choice:
            return

        try:

            indices = [
                int(x) - 1
                for x in choice.split()
            ]

        except ValueError:

            messagebox.showerror(
                "Erreur",
                "Positions invalides."
            )

            return

        indices = sorted(
            set(indices),
            reverse=True
        )

        if any(
            i < 0 or i >= len(player.rack)
            for i in indices
        ):

            messagebox.showerror(
                "Erreur",
                "Une position est invalide."
            )

            return

        if len(indices) > self.tile_bag.remaining():

            messagebox.showwarning(
                "Échange",
                "Pas assez de lettres dans le sac."
            )

            return

        old_tiles = []

        for index in indices:

            old_tiles.append(
                player.rack.pop(index)
            )

        new_tiles = self.tile_bag.draw_multiple(
            len(old_tiles)
        )

        player.rack.extend(
            new_tiles
        )

        self.tile_bag.put_back(
            old_tiles
        )

        self.consecutive_passes = 0

        self.next_turn()

    # =========================================================
    # TOUR SUIVANT
    # =========================================================

    def next_turn(self):

        self.current_player += 1

        if self.current_player >= self.number_of_players:

            self.current_player = 0

        self.update_interface()

    # =========================================================
    # FIN DE PARTIE
    # =========================================================

    def end_game(self):

        # Soustraction des lettres restantes
        for player in self.players:

            penalty = sum(
                TILE_VALUES[tile]
                for tile in player.rack
            )

            player.score -= penalty

        ranking = sorted(
            self.players,
            key=lambda p: p.score,
            reverse=True
        )

        text = "FIN DE PARTIE\n\n"

        for i, player in enumerate(ranking):

            text += (
                f"{i + 1}. "
                f"{player.name} : "
                f"{player.score} points\n"
            )

        messagebox.showinfo(
            "Fin de partie",
            text
        )

        self.root.destroy()
