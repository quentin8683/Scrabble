import json
import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import time

BOARD_SIZE = 15


class NetworkGame:
    def __init__(self, root, client, name):
        self.root = root
        self.client = client  # On reçoit le client HTTP
        self.name = name
        self.player_index = client.player_index

        self.state = None
        self.selected_index = None
        self.alive = True

        self.create_interface()
        self.update_loop()

    # =========================================================
    # INTERFACE
    # =========================================================

    def create_interface(self):
        self.root.title("Scrabble — Réseau")
        self.root.geometry("1250x850")
        self.root.configure(bg="#1f2937")

        self.main_frame = tk.Frame(self.root, bg="#1f2937")
        self.main_frame.pack(fill="both", expand=True)

        # Plateau
        self.board_frame = tk.Frame(self.main_frame, bg="#1f2937")
        self.board_frame.pack(side="left", padx=20, pady=20)

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
                    command=lambda r=row, c=col: self.board_click(r, c)
                )
                button.grid(row=row, column=col, padx=1, pady=1)
                row_cells.append(button)
            self.cells.append(row_cells)

        # Panneau droit
        self.side_frame = tk.Frame(self.main_frame, bg="#111827")
        self.side_frame.pack(side="right", fill="y", padx=10, pady=20)

        tk.Label(
            self.side_frame,
            text="SCRABBLE RÉSEAU",
            font=("Arial", 24, "bold"),
            fg="white",
            bg="#111827"
        ).pack(pady=15)

        self.status = tk.Label(
            self.side_frame,
            text="Connexion...",
            font=("Arial", 12),
            fg="#9ca3af",
            bg="#111827"
        )
        self.status.pack(pady=5)

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
            text="Votre chevalet",
            font=("Arial", 15, "bold"),
            fg="white",
            bg="#111827"
        ).pack(pady=5)

        self.rack_frame = tk.Frame(self.side_frame, bg="#111827")
        self.rack_frame.pack()

        # Boutons
        self.play_button = tk.Button(
            self.side_frame,
            text="JOUER LE MOT",
            font=("Arial", 12, "bold"),
            bg="#16a34a",
            fg="white",
            command=self.play
        )
        self.play_button.pack(fill="x", padx=25, pady=8)

        self.cancel_button = tk.Button(
            self.side_frame,
            text="Annuler",
            command=self.cancel
        )
        self.cancel_button.pack(fill="x", padx=25, pady=4)

        self.pass_button = tk.Button(
            self.side_frame,
            text="Passer",
            command=self.pass_turn
        )
        self.pass_button.pack(fill="x", padx=25, pady=4)

        self.exchange_button = tk.Button(
            self.side_frame,
            text="Échanger",
            command=self.exchange
        )
        self.exchange_button.pack(fill="x", padx=25, pady=4)

        self.remaining_label = tk.Label(
            self.side_frame,
            text="",
            fg="#9ca3af",
            bg="#111827"
        )
        self.remaining_label.pack(pady=15)

    # =========================================================
    # MISE À JOUR (POLLING)
    # =========================================================

    def update_loop(self):
        if not self.alive:
            return

        # Appel toutes les 2 secondes
        self.update_state()
        self.root.after(2000, self.update_loop)

    def update_state(self):
        try:
            state = self.client.get_state()
            if 'error' in state:
                self.status.config(text=f"⚠️ {state['error']}", fg="#ef4444")
                return

            self.state = state
            self.selected_index = None
            self.update_interface()

        except Exception as e:
            self.status.config(text=f"⚠️ Erreur : {str(e)[:30]}", fg="#ef4444")

    # =========================================================
    # AFFICHAGE (identique à votre version)
    # =========================================================

    def update_interface(self):
        if self.state is None:
            return

        board = self.state["board"]

        # Plateau
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                button = self.cells[row][col]
                value = board[row][col]
                if value is None:
                    button.config(text="", bg="#e5e7eb", fg="black")
                else:
                    letter = value[0] if isinstance(value, list) else value
                    button.config(text=letter, bg="#f59e0b", fg="black")

        # Cases temporaires
        for pending in self.state.get("pending", []):
            row = pending["row"]
            col = pending["col"]
            letter = pending["letter"]
            self.cells[row][col].config(text=letter, bg="#22c55e", fg="black")

        # Tour
        current_player = self.state["current_player"]
        current_name = self.state["players"][current_player]["name"]
        self.turn_label.config(text=f"Tour de {current_name}")

        # Scores
        score_text = ""
        for player in self.state["players"]:
            score_text += f"{player['name']} : {player['score']}\n"
        self.score_label.config(text=score_text)

        # Chevalet
        for widget in self.rack_frame.winfo_children():
            widget.destroy()

        rack = self.state.get("rack", [])
        for index, tile in enumerate(rack):
            display = "?" if tile == "?" else tile
            button = tk.Button(
                self.rack_frame,
                text=display,
                width=4,
                height=2,
                font=("Arial", 11, "bold"),
                command=lambda i=index: self.select_tile(i)
            )
            button.grid(row=0, column=index, padx=2)

        # Informations
        self.remaining_label.config(
            text=f"Lettres dans le sac : {self.state['remaining']}"
        )

        # Tour du joueur
        if self.player_index == current_player:
            self.status.config(text="À VOUS DE JOUER !", fg="#22c55e")
        else:
            self.status.config(text="En attente du joueur adverse…", fg="#9ca3af")

    # =========================================================
    # SÉLECTION TUILE
    # =========================================================

    def select_tile(self, index):
        if self.state is None:
            return
        if self.player_index != self.state["current_player"]:
            return
        self.selected_index = index

    # =========================================================
    # PLACER SUR LE PLATEAU
    # =========================================================

    def board_click(self, row, col):
        if self.state is None:
            return
        if self.player_index != self.state["current_player"]:
            return
        if self.state["board"][row][col] is not None:
            return
        if self.selected_index is None:
            return

        rack = self.state.get("rack", [])
        if self.selected_index >= len(rack):
            return

        tile = rack[self.selected_index]
        joker = None

        if tile == "?":
            joker = simpledialog.askstring(
                "Joker",
                "Quelle lettre représente le joker ?",
                parent=self.root
            )
            if not joker:
                return
            joker = joker.strip().upper()
            if len(joker) != 1 or not joker.isalpha():
                messagebox.showerror("Joker", "Entre une seule lettre.")
                return

        self.client.place(row, col, self.selected_index, joker)
        self.selected_index = None

    # =========================================================
    # ACTIONS
    # =========================================================

    def play(self):
        if self.state is None:
            return
        if self.player_index != self.state["current_player"]:
            return
        self.client.play()

    def cancel(self):
        if self.state is None:
            return
        if self.player_index != self.state["current_player"]:
            return
        self.client.cancel()

    def pass_turn(self):
        if self.state is None:
            return
        if self.player_index != self.state["current_player"]:
            return
        self.client.pass_turn()

    def exchange(self):
        if self.state is None:
            return
        if self.player_index != self.state["current_player"]:
            return

        choice = simpledialog.askstring(
            "Échanger",
            "Positions des lettres à échanger\nExemple : 1 3 5",
            parent=self.root
        )
        if not choice:
            return

        try:
            indices = [int(value) - 1 for value in choice.split()]
        except ValueError:
            messagebox.showerror("Échange", "Positions invalides.")
            return

        self.client.exchange(indices)

    # =========================================================
    # FERMETURE
    # =========================================================

    def close(self):
        self.alive = False
