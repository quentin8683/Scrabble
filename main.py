import tkinter as tk
from tkinter import messagebox

from network_game import NetworkGame
from network_server import ScrabbleServer


class StartScreen:

    def __init__(
        self,
        root
    ):

        self.root = root

        self.root.title(
            "Scrabble"
        )

        self.root.geometry(
            "550x600"
        )

        self.root.resizable(
            False,
            False
        )

        self.root.configure(
            bg="#1f2937"
        )

        self.create_interface()

    # =========================================================
    # INTERFACE
    # =========================================================

    def create_interface(self):

        self.frame = tk.Frame(
            self.root,
            bg="#1f2937"
        )

        self.frame.pack(
            fill="both",
            expand=True
        )

        # -----------------------------------------------------
        # TITRE
        # -----------------------------------------------------

        tk.Label(
            self.frame,
            text="SCRABBLE",
            font=(
                "Arial",
                34,
                "bold"
            ),
            fg="white",
            bg="#1f2937"
        ).pack(
            pady=(45, 5)
        )

        tk.Label(
            self.frame,
            text="Jouez avec vos collègues",
            font=(
                "Arial",
                13
            ),
            fg="#9ca3af",
            bg="#1f2937"
        ).pack(
            pady=(0, 30)
        )

        # -----------------------------------------------------
        # NOM
        # -----------------------------------------------------

        tk.Label(
            self.frame,
            text="Votre nom",
            font=(
                "Arial",
                14,
                "bold"
            ),
            fg="white",
            bg="#1f2937"
        ).pack(
            pady=(5, 5)
        )

        self.name_entry = tk.Entry(
            self.frame,
            font=(
                "Arial",
                14
            ),
            justify="center",
            width=25
        )

        self.name_entry.insert(
            0,
            "Joueur"
        )

        self.name_entry.pack(
            pady=5
        )

        # -----------------------------------------------------
        # CREER PARTIE
        # -----------------------------------------------------

        tk.Button(
            self.frame,
            text="🏠  CRÉER UNE PARTIE",
            font=(
                "Arial",
                14,
                "bold"
            ),
            bg="#16a34a",
            fg="white",
            activebackground="#15803d",
            activeforeground="white",
            padx=20,
            pady=12,
            command=self.create_game
        ).pack(
            fill="x",
            padx=90,
            pady=(30, 10)
        )

        # -----------------------------------------------------
        # SEPARATEUR
        # -----------------------------------------------------

        tk.Label(
            self.frame,
            text="OU",
            font=(
                "Arial",
                11,
                "bold"
            ),
            fg="#6b7280",
            bg="#1f2937"
        ).pack(
            pady=8
        )

        # -----------------------------------------------------
        # IP
        # -----------------------------------------------------

        tk.Label(
            self.frame,
            text="IP du PC qui héberge",
            font=(
                "Arial",
                14,
                "bold"
            ),
            fg="white",
            bg="#1f2937"
        ).pack(
            pady=(10, 5)
        )

        self.host_entry = tk.Entry(
            self.frame,
            font=(
                "Arial",
                14
            ),
            justify="center",
            width=25
        )

        self.host_entry.insert(
            0,
            "192.168.1.42"
        )

        self.host_entry.pack(
            pady=5
        )

        # -----------------------------------------------------
        # PORT
        # -----------------------------------------------------

        tk.Label(
            self.frame,
            text="Port",
            font=(
                "Arial",
                12
            ),
            fg="#d1d5db",
            bg="#1f2937"
        ).pack(
            pady=(12, 3)
        )

        self.port_entry = tk.Entry(
            self.frame,
            font=(
                "Arial",
                12
            ),
            justify="center",
            width=10
        )

        self.port_entry.insert(
            0,
            "5050"
        )

        self.port_entry.pack()

        # -----------------------------------------------------
        # REJOINDRE
        # -----------------------------------------------------

        tk.Button(
            self.frame,
            text="🌐  REJOINDRE LA PARTIE",
            font=(
                "Arial",
                14,
                "bold"
            ),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            padx=20,
            pady=12,
            command=self.join_game
        ).pack(
            fill="x",
            padx=90,
            pady=20
        )

    # =========================================================
    # NOM
    # =========================================================

    def get_name(self):

        name = (
            self.name_entry
            .get()
            .strip()
        )

        if not name:
            return "Joueur"

        return name[:30]

    # =========================================================
    # PORT
    # =========================================================

    def get_port(self):

        try:

            port = int(
                self.port_entry
                .get()
            )

        except ValueError:

            messagebox.showerror(
                "Réseau",
                "Le port doit être un nombre."
            )

            return None

        if (
            port < 1
            or
            port > 65535
        ):

            messagebox.showerror(
                "Réseau",
                "Le port doit être compris entre 1 et 65535."
            )

            return None

        return port

    # =========================================================
    # CREER UNE PARTIE
    # =========================================================

    def create_game(self):

        name = self.get_name()

        port = self.get_port()

        if port is None:
            return

        try:

            # -------------------------------------------------
            # CREATION DU SERVEUR
            # -------------------------------------------------

            server = ScrabbleServer(
                host="0.0.0.0",
                port=port,
                max_players=4
            )

            # -------------------------------------------------
            # SERVEUR DANS UN THREAD
            # -------------------------------------------------

            import threading

            server_thread = threading.Thread(
                target=server.run,
                daemon=True
            )

            server_thread.start()

            # Garder une référence
            self.root.scrabble_server = server

            # -------------------------------------------------
            # CONNEXION AUTOMATIQUE DU CREATEUR
            # -------------------------------------------------

            self.root.after(
                500,
                lambda:
                    self.start_client(
                        "127.0.0.1",
                        port,
                        name
                    )
            )

        except Exception as error:

            messagebox.showerror(
                "Serveur",
                f"Impossible de créer la partie :\n\n{error}"
            )

    # =========================================================
    # REJOINDRE
    # =========================================================

    def join_game(self):

        host = (
            self.host_entry
            .get()
            .strip()
        )

        name = self.get_name()

        port = self.get_port()

        if port is None:
            return

        if not host:

            messagebox.showerror(
                "Réseau",
                "Indique l'adresse IP du serveur."
            )

            return

        self.start_client(
            host,
            port,
            name
        )

    # =========================================================
    # LANCER LE CLIENT
    # =========================================================

    def start_client(
        self,
        host,
        port,
        name
    ):

        try:

            self.frame.destroy()

            NetworkGame(
                self.root,
                host,
                port,
                name
            )

        except RuntimeError as error:

            messagebox.showerror(
                "Connexion",
                str(error)
            )

            # Revenir à l'écran d'accueil
            self.create_interface()


# =============================================================
# MAIN
# =============================================================

def main():

    root = tk.Tk()

    try:

        StartScreen(
            root
        )

        root.mainloop()

    except FileNotFoundError as error:

        messagebox.showerror(
            "Dictionnaire",
            str(error)
        )


if __name__ == "__main__":

    main()