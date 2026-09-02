import json
import socket
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog


BOARD_SIZE = 15


class NetworkGame:

    def __init__(
        self,
        root,
        host,
        port,
        name
    ):

        self.root = root

        self.host = host
        self.port = port
        self.name = name

        self.player_index = None

        self.state = None

        self.selected_index = None

        self.sock = None

        self.reader = None

        self.alive = True

        self.connect()

        self.create_interface()

    # =========================================================
    # CONNEXION
    # =========================================================

    def connect(self):

        try:

            self.sock = socket.create_connection(
                (
                    self.host,
                    self.port
                ),
                timeout=8
            )

            self.sock.settimeout(
                None
            )

            self.send(
                {
                    "type": "join",
                    "name": self.name
                }
            )

            self.reader = self.sock.makefile(
                "r",
                encoding="utf-8"
            )

            threading.Thread(
                target=self.receive_loop,
                daemon=True
            ).start()

        except OSError as error:

            raise RuntimeError(
                f"Impossible de se connecter au serveur :\n\n"
                f"{error}"
            )

    # =========================================================
    # ENVOI
    # =========================================================

    def send(
        self,
        data
    ):

        if not self.sock:
            return

        try:

            message = (
                json.dumps(
                    data,
                    ensure_ascii=False
                )
                + "\n"
            )

            self.sock.sendall(
                message.encode(
                    "utf-8"
                )
            )

        except OSError:

            self.connection_lost()

    # =========================================================
    # RECEPTION
    # =========================================================

    def receive_loop(self):

        try:

            for line in self.reader:

                if not line.strip():
                    continue

                message = json.loads(
                    line
                )

                self.root.after(
                    0,
                    self.handle_message,
                    message
                )

        except (
            OSError,
            ConnectionError,
            json.JSONDecodeError
        ):

            self.root.after(
                0,
                self.connection_lost
            )

    # =========================================================
    # MESSAGES SERVEUR
    # =========================================================

    def handle_message(
        self,
        message
    ):

        message_type = message.get(
            "type"
        )

        # -----------------------------------------------------
        # CONNEXION
        # -----------------------------------------------------

        if message_type == "joined":

            self.player_index = (
                message["player_index"]
            )

            self.status.config(
                text="Connecté. En attente..."
            )

        # -----------------------------------------------------
        # PARTIE DEMARREE
        # -----------------------------------------------------

        elif message_type == "started":

            self.status.config(
                text="La partie commence !"
            )

        # -----------------------------------------------------
        # ETAT DU JEU
        # -----------------------------------------------------

        elif message_type == "state":

            self.state = message[
                "state"
            ]

            self.selected_index = None

            self.update_interface()

        # -----------------------------------------------------
        # ERREUR
        # -----------------------------------------------------

        elif message_type == "error":

            messagebox.showerror(
                "Scrabble",
                message.get(
                    "message",
                    "Erreur inconnue."
                )
            )

        # -----------------------------------------------------
        # INFORMATION
        # -----------------------------------------------------

        elif message_type == "info":

            self.status.config(
                text=message.get(
                    "message",
                    ""
                )
            )

        # -----------------------------------------------------
        # FIN
        # -----------------------------------------------------

        elif message_type == "game_over":

            ranking = "\n".join(
                f"{i + 1}. "
                f"{player['name']} : "
                f"{player['score']} points"
                for i, player
                in enumerate(
                    message["ranking"]
                )
            )

            messagebox.showinfo(
                "Fin de partie",
                "FIN DE PARTIE\n\n"
                + ranking
            )

            self.status.config(
                text="Partie terminée."
            )

    # =========================================================
    # DECONNEXION
    # =========================================================

    def connection_lost(self):

        if not self.alive:
            return

        self.alive = False

        if hasattr(
            self,
            "status"
        ):

            self.status.config(
                text="Connexion au serveur perdue."
            )

    # =========================================================
    # INTERFACE
    # =========================================================

    def create_interface(self):

        self.root.title(
            "Scrabble — Réseau"
        )

        self.root.geometry(
            "1250x850"
        )

        self.root.configure(
            bg="#1f2937"
        )

        # -----------------------------------------------------
        # PRINCIPAL
        # -----------------------------------------------------

        self.main_frame = tk.Frame(
            self.root,
            bg="#1f2937"
        )

        self.main_frame.pack(
            fill="both",
            expand=True
        )

        # -----------------------------------------------------
        # PLATEAU
        # -----------------------------------------------------

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

        for row in range(
            BOARD_SIZE
        ):

            row_cells = []

            for col in range(
                BOARD_SIZE
            ):

                button = tk.Button(
                    self.board_frame,
                    text="",
                    width=3,
                    height=1,
                    font=(
                        "Arial",
                        10,
                        "bold"
                    ),
                    command=lambda r=row, c=col:
                        self.board_click(
                            r,
                            c
                        )
                )

                button.grid(
                    row=row,
                    column=col,
                    padx=1,
                    pady=1
                )

                row_cells.append(
                    button
                )

            self.cells.append(
                row_cells
            )

        # -----------------------------------------------------
        # PANNEAU DROIT
        # -----------------------------------------------------

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
            text="SCRABBLE RÉSEAU",
            font=(
                "Arial",
                24,
                "bold"
            ),
            fg="white",
            bg="#111827"
        ).pack(
            pady=15
        )

        self.status = tk.Label(
            self.side_frame,
            text="Connexion...",
            font=(
                "Arial",
                12
            ),
            fg="#9ca3af",
            bg="#111827"
        )

        self.status.pack(
            pady=5
        )

        self.turn_label = tk.Label(
            self.side_frame,
            text="",
            font=(
                "Arial",
                16,
                "bold"
            ),
            fg="#60a5fa",
            bg="#111827"
        )

        self.turn_label.pack(
            pady=10
        )

        self.score_label = tk.Label(
            self.side_frame,
            text="",
            font=(
                "Arial",
                13
            ),
            fg="white",
            bg="#111827",
            justify="left"
        )

        self.score_label.pack(
            pady=10
        )

        tk.Label(
            self.side_frame,
            text="Votre chevalet",
            font=(
                "Arial",
                15,
                "bold"
            ),
            fg="white",
            bg="#111827"
        ).pack(
            pady=5
        )

        self.rack_frame = tk.Frame(
            self.side_frame,
            bg="#111827"
        )

        self.rack_frame.pack()

        # -----------------------------------------------------
        # BOUTONS
        # -----------------------------------------------------

        self.play_button = tk.Button(
            self.side_frame,
            text="JOUER LE MOT",
            font=(
                "Arial",
                12,
                "bold"
            ),
            bg="#16a34a",
            fg="white",
            command=self.play
        )

        self.play_button.pack(
            fill="x",
            padx=25,
            pady=8
        )

        self.cancel_button = tk.Button(
            self.side_frame,
            text="Annuler",
            command=self.cancel
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
            command=self.exchange
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

        self.remaining_label.pack(
            pady=15
        )

    # =========================================================
    # AFFICHAGE
    # =========================================================

    def update_interface(self):

        if self.state is None:
            return

        board = self.state[
            "board"
        ]

        # -----------------------------------------------------
        # PLATEAU
        # -----------------------------------------------------

        for row in range(
            BOARD_SIZE
        ):

            for col in range(
                BOARD_SIZE
            ):

                button = self.cells[
                    row
                ][
                    col
                ]

                value = board[
                    row
                ][
                    col
                ]

                if value is None:

                    button.config(
                        text="",
                        bg="#e5e7eb",
                        fg="black"
                    )

                else:

                    if isinstance(
                        value,
                        list
                    ):

                        letter = value[0]

                    else:

                        letter = value

                    button.config(
                        text=letter,
                        bg="#f59e0b",
                        fg="black"
                    )

        # -----------------------------------------------------
        # CASES TEMPORAIRES
        # -----------------------------------------------------

        for pending in self.state.get(
            "pending",
            []
        ):

            row = pending[
                "row"
            ]

            col = pending[
                "col"
            ]

            letter = pending[
                "letter"
            ]

            self.cells[
                row
            ][
                col
            ].config(
                text=letter,
                bg="#22c55e",
                fg="black"
            )

        # -----------------------------------------------------
        # TOUR
        # -----------------------------------------------------

        current_player = (
            self.state[
                "current_player"
            ]
        )

        current_name = (
            self.state[
                "players"
            ][
                current_player
            ][
                "name"
            ]
        )

        self.turn_label.config(
            text=f"Tour de {current_name}"
        )

        # -----------------------------------------------------
        # SCORES
        # -----------------------------------------------------

        score_text = ""

        for player in self.state[
            "players"
        ]:

            score_text += (
                f"{player['name']} : "
                f"{player['score']}\n"
            )

        self.score_label.config(
            text=score_text
        )

        # -----------------------------------------------------
        # CHEVALET
        # -----------------------------------------------------

        for widget in (
            self.rack_frame.winfo_children()
        ):

            widget.destroy()

        rack = self.state.get(
            "rack",
            []
        )

        for index, tile in enumerate(
            rack
        ):

            display = (
                "?"
                if tile == "?"
                else tile
            )

            button = tk.Button(
                self.rack_frame,
                text=display,
                width=4,
                height=2,
                font=(
                    "Arial",
                    11,
                    "bold"
                ),
                command=lambda i=index:
                    self.select_tile(i)
            )

            button.grid(
                row=0,
                column=index,
                padx=2
            )

        # -----------------------------------------------------
        # INFORMATIONS
        # -----------------------------------------------------

        self.remaining_label.config(
            text=(
                "Lettres dans le sac : "
                f"{self.state['remaining']}"
            )
        )

        # -----------------------------------------------------
        # TOUR DU JOUEUR
        # -----------------------------------------------------

        if (
            self.player_index
            ==
            current_player
        ):

            self.status.config(
                text="À VOUS DE JOUER !",
                fg="#22c55e"
            )

        else:

            self.status.config(
                text="En attente du joueur adverse…",
                fg="#9ca3af"
            )

    # =========================================================
    # SELECTION TUILE
    # =========================================================

    def select_tile(
        self,
        index
    ):

        if self.state is None:
            return

        if (
            self.player_index
            !=
            self.state[
                "current_player"
            ]
        ):
            return

        self.selected_index = index

    # =========================================================
    # PLACER SUR LE PLATEAU
    # =========================================================

    def board_click(
        self,
        row,
        col
    ):

        if self.state is None:
            return

        # Pas notre tour
        if (
            self.player_index
            !=
            self.state[
                "current_player"
            ]
        ):
            return

        # Case occupée
        if (
            self.state[
                "board"
            ][
                row
            ][
                col
            ]
            is not None
        ):
            return

        # Aucune tuile sélectionnée
        if self.selected_index is None:
            return

        rack = self.state.get(
            "rack",
            []
        )

        if (
            self.selected_index
            >=
            len(rack)
        ):
            return

        tile = rack[
            self.selected_index
        ]

        joker = None

        # -----------------------------------------------------
        # JOKER
        # -----------------------------------------------------

        if tile == "?":

            joker = simpledialog.askstring(
                "Joker",
                "Quelle lettre représente le joker ?",
                parent=self.root
            )

            if not joker:
                return

            joker = joker.strip().upper()

            if (
                len(joker) != 1
                or
                not joker.isalpha()
            ):

                messagebox.showerror(
                    "Joker",
                    "Entre une seule lettre."
                )

                return

        # -----------------------------------------------------
        # ENVOI SERVEUR
        # -----------------------------------------------------

        self.send(
            {
                "type": "place",
                "row": row,
                "col": col,
                "rack_index":
                    self.selected_index,
                "joker": joker
            }
        )

        self.selected_index = None

    # =========================================================
    # JOUER
    # =========================================================

    def play(self):

        if self.state is None:
            return

        if (
            self.player_index
            !=
            self.state[
                "current_player"
            ]
        ):
            return

        self.send(
            {
                "type": "play"
            }
        )

    # =========================================================
    # ANNULER
    # =========================================================

    def cancel(self):

        if self.state is None:
            return

        if (
            self.player_index
            !=
            self.state[
                "current_player"
            ]
        ):
            return

        self.send(
            {
                "type": "cancel"
            }
        )

    # =========================================================
    # PASSER
    # =========================================================

    def pass_turn(self):

        if self.state is None:
            return

        if (
            self.player_index
            !=
            self.state[
                "current_player"
            ]
        ):
            return

        self.send(
            {
                "type": "pass"
            }
        )

    # =========================================================
    # ECHANGER
    # =========================================================

    def exchange(self):

        if self.state is None:
            return

        if (
            self.player_index
            !=
            self.state[
                "current_player"
            ]
        ):
            return

        choice = simpledialog.askstring(
            "Échanger",
            "Positions des lettres à échanger\n"
            "Exemple : 1 3 5",
            parent=self.root
        )

        if not choice:
            return

        try:

            indices = [
                int(value) - 1
                for value
                in choice.split()
            ]

        except ValueError:

            messagebox.showerror(
                "Échange",
                "Positions invalides."
            )

            return

        self.send(
            {
                "type": "exchange",
                "indices": indices
            }
        )

    # =========================================================
    # FERMETURE
    # =========================================================

    def close(self):

        self.alive = False

        try:

            if self.sock:
                self.sock.close()

        except OSError:
            pass