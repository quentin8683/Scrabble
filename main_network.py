import json
import tkinter as tk
from tkinter import messagebox, simpledialog
import threading
import time
from functools import partial

BOARD_SIZE = 15


class NetworkGame:
    def __init__(self, root, client, name):
        self.root = root
        self.client = client
        self.name = name
        self.player_index = client.player_index
        self.state = None
        self.selected_index = None
        self.alive = True
        self.game_started = False

        print(f"🟢 NetworkGame initialisé pour {name} (index {self.player_index})")

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
                    command=partial(self.board_click, row, col)
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

        # Initialiser l'affichage en attente
        self.show_waiting()

    def show_waiting(self):
        """Affiche l'écran d'attente"""
        self.status.config(text="⏳ En attente du début de la partie...", fg="#fcd34d")
        self.turn_label.config(text="")
        self.score_label.config(text="")
        self.remaining_label.config(text="")
        self.play_button.config(state="disabled")
        self.cancel_button.config(state="disabled")
        self.pass_button.config(state="disabled")
        self.exchange_button.config(state="disabled")

    # =========================================================
    # MISE À JOUR (POLLING)
    # =========================================================

    def update_loop(self):
        if not self.alive:
            return

        self.update_state()
        self.root.after(2000, self.update_loop)

    def update_state(self):
        try:
            state = self.client.get_state()
            if 'error' in state:
                self.status.config(text=f"⚠️ {state['error']}", fg="#ef4444")
                return

            print(f"📊 État reçu : {state}")

            # Vérifier si la partie a commencé
            if not state.get('game_started', False) or 'board' not in state:
                self.show_waiting()
                self.status.config(
                    text=f"⏳ En attente des joueurs... ({len(state.get('players', []))}/2)",
                    fg="#fcd34d"
                )
                return

            # Partie commencée
            self.game_started = True
            self.state = state
            self.selected_index = None
            self.update_interface()

        except Exception as e:
            print(f"❌ Erreur update_state : {e}")
            self.status.config(text=f"⚠️ Erreur : {str(e)[:30]}", fg="#ef4444")

    # =========================================================
    # AFFICHAGE
    # =========================================================

    def update_interface(self):
        if self.state is None or not self.game_started:
            return

        # Activer les boutons
        self.play_button.config(state="normal")
        self.cancel_button.config(state="normal")
        self.pass_button.config(state="normal")
        self.exchange_button.config(state="normal")

        board = self.state.get("board", [])

        # Plateau
        for row in range(BOARD_SIZE):
            for col in range(BOARD_SIZE):
                button = self.cells[row][col]
                try:
                    value = board[row][col]
                except (IndexError, TypeError):
                    button.config(text="", bg="#e5e7eb", fg="black")
                    continue

                if value is None:
                    # Multiplicateurs
                    multiplier = self.state.get("multiplier_grid", None)
                    if multiplier and row < len(multiplier) and col < len(multiplier[row]) and multiplier[row][col]:
                        m = multiplier[row][col]
                        text = self.multiplier_text(m)
                        color = self.multiplier_color(m)
                        button.config(text=text, bg=color, fg="black")
                    else:
                        button.config(text="", bg="#e5e7eb", fg="black")
                else:
                    letter = value[0] if isinstance(value, list) else value
                    button.config(text=letter, bg="#f59e0b", fg="black")

        # Cases temporaires
        for pending in self.state.get("pending", []):
            row = pending["row"]
            col = pending["col"]
            letter = pending["letter"]
            if row < BOARD_SIZE and col < BOARD_SIZE:
                self.cells[row][col].config(text=letter, bg="#22c55e", fg="black")

        # Tour
        current_player = self.state.get("current_player", 0)
        players = self.state.get("players", [])
        if players and current_player < len(players):
            current_name = players[current_player].get("name", "Inconnu")
            self.turn_label.config(text=f"Tour de {current_name}")
        else:
            self.turn_label.config(text="")

        # Scores
        score_text = ""
        for player in players:
            score_text += f"{player.get('name', '?')} : {player.get('score', 0)}\n"
        self.score_label.config(text=score_text)

        # Chevalet
        for widget in self.rack_frame.winfo_children():
            widget.destroy()

        rack = self.state.get("rack", [])
        print(f"🃏 Chevalet : {rack}")
        for index, tile in enumerate(rack):
            display = "?" if tile == "?" else tile
            button = tk.Button(
                self.rack_frame,
                text=display,
                width=4,
                height=2,
                font=("Arial", 11, "bold"),
                command=partial(self.select_tile, index)
            )
            button.grid(row=0, column=index, padx=2)

        # Informations
        self.remaining_label.config(
            text=f"Lettres dans le sac : {self.state.get('remaining', 0)}"
        )

        # Tour du joueur
        if self.player_index == current_player:
            self.status.config(text="✅ À VOUS DE JOUER !", fg="#22c55e")
            print("✅ C'est mon tour !")
        else:
            self.status.config(text="⏳ En attente du joueur adverse…", fg="#9ca3af")
            print("⏳ Pas mon tour")

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
        }.get(multiplier, "#e5e7eb")

    # =========================================================
    # SÉLECTION TUILE
    # =========================================================

    def select_tile(self, index):
        print(f"🖱️ Tuile sélectionnée : {index}")
        if self.state is None or not self.game_started:
            return
        if self.player_index != self.state.get("current_player", -1):
            print("❌ Pas mon tour, sélection ignorée")
            return
        self.selected_index = index
        print(f"✅ Tuile {index} sélectionnée")

    # =========================================================
    # PLACER SUR LE PLATEAU
    # =========================================================

    def board_click(self, row, col):
        print(f"🖱️ Clic sur le plateau : ({row}, {col})")
        
        if self.state is None or not self.game_started:
            print("❌ État non disponible ou partie pas commencée")
            return
            
        if self.player_index != self.state.get("current_player", -1):
            print("❌ Pas mon tour")
            return
        
        try:
            if self.state["board"][row][col] is not None:
                print("❌ Case occupée")
                return
        except (IndexError, TypeError):
            print("❌ Case invalide")
            return
            
        if self.selected_index is None:
            print("❌ Aucune tuile sélectionnée")
            return

        rack = self.state.get("rack", [])
        if self.selected_index >= len(rack):
            print("❌ Index de tuile invalide")
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

        print(f"📤 Envoi de la tuile {tile} en ({row}, {col})")
        
        try:
            result = self.client.place(row, col, self.selected_index, joker)
            print(f"📥 Réponse : {result}")
            
            if 'error' in result:
                messagebox.showerror("Erreur", result['error'])
            elif result.get('success') == False and result.get('error'):
                messagebox.showerror("Erreur", result['error'])
            else:
                self.selected_index = None
                print("✅ Tuile placée avec succès")
                
        except Exception as e:
            print(f"❌ Erreur lors du placement : {e}")
            messagebox.showerror("Erreur", str(e))

    # =========================================================
    # ACTIONS
    # =========================================================

    def play(self):
        print("🎮 JOUER LE MOT")
        if self.state is None or not self.game_started:
            return
        if self.player_index != self.state.get("current_player", -1):
            return
        
        try:
            result = self.client.play()
            print(f"📥 Réponse play : {result}")
            if 'error' in result:
                messagebox.showerror("Erreur", result['error'])
            elif result.get('success') == False and result.get('error'):
                messagebox.showerror("Erreur", result['error'])
        except Exception as e:
            print(f"❌ Erreur play : {e}")
            messagebox.showerror("Erreur", str(e))

    def cancel(self):
        print("❌ ANNULER")
        if self.state is None or not self.game_started:
            return
        if self.player_index != self.state.get("current_player", -1):
            return
        
        try:
            result = self.client.cancel()
            print(f"📥 Réponse cancel : {result}")
            if 'error' in result:
                messagebox.showerror("Erreur", result['error'])
        except Exception as e:
            print(f"❌ Erreur cancel : {e}")
            messagebox.showerror("Erreur", str(e))

    def pass_turn(self):
        print("⏭️ PASSER")
        if self.state is None or not self.game_started:
            return
        if self.player_index != self.state.get("current_player", -1):
            return
        
        try:
            result = self.client.pass_turn()
            print(f"📥 Réponse pass : {result}")
            if 'error' in result:
                messagebox.showerror("Erreur", result['error'])
        except Exception as e:
            print(f"❌ Erreur pass : {e}")
            messagebox.showerror("Erreur", str(e))

    def exchange(self):
        print("🔄 ÉCHANGER")
        if self.state is None or not self.game_started:
            return
        if self.player_index != self.state.get("current_player", -1):
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

        try:
            result = self.client.exchange(indices)
            print(f"📥 Réponse exchange : {result}")
            if 'error' in result:
                messagebox.showerror("Erreur", result['error'])
        except Exception as e:
            print(f"❌ Erreur exchange : {e}")
            messagebox.showerror("Erreur", str(e))

    def close(self):
        self.alive = False
