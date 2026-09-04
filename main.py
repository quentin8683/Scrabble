import tkinter as tk
from tkinter import messagebox
import requests
import urllib3
import threading
import time
import json as json_lib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ============================================================
# CLIENT HTTP POUR RENDER (CORRIGÉ)
# ============================================================

class ScrabbleClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.player_index = None
        self.game_started = False

    def _safe_request(self, method, endpoint, **kwargs):
        """Méthode sécurisée pour faire une requête HTTP"""
        url = f"{self.server_url}{endpoint}"
        try:
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            kwargs['headers']['Content-Type'] = 'application/json'

            response = requests.request(method, url, verify=False, timeout=60, **kwargs)

            if response.status_code != 200:
                # Le serveur renvoie souvent un JSON détaillé même en cas
                # d'erreur (ex: 400 pour un mot invalide), avec l'explication
                # précise dans "error". On essaie de le lire avant d'abandonner.
                content = response.text.strip()
                if content.startswith(('{', '[')):
                    try:
                        data = response.json()
                        if isinstance(data, dict) and data.get('error'):
                            return data
                    except ValueError:
                        pass
                return {"error": f"HTTP {response.status_code}"}

            content = response.text.strip()
            if not content:
                return {"error": "Réponse vide"}

            if not content.startswith(('{', '[')):
                return {
                    "error": f"Réponse inattendue (non-JSON)",
                    "raw": content[:200]
                }

            return response.json()

        except requests.exceptions.Timeout:
            return {"error": "Délai d'attente dépassé (60s)"}
        except requests.exceptions.ConnectionError:
            return {"error": "Impossible de contacter le serveur"}
        except ValueError as e:
            return {"error": f"Erreur de décodage JSON : {str(e)}"}
        except Exception as e:
            return {"error": str(e)}

    def get_status(self):
        """Consulte l'état du serveur sans être connecté (avant /join)"""
        return self._safe_request('GET', '/status')

    def join(self, name, max_players):
        result = self._safe_request('POST', '/join', json={
            "name": name,
            "max_players": max_players
        })
        if 'error' not in result:
            self.player_index = result.get('player_index')
            self.game_started = result.get('game_started', False)
        return result

    def get_state(self):
        if self.player_index is None:
            return {"error": "Pas de joueur connecté"}
        return self._safe_request(
            'GET', '/state',
            params={"player_index": self.player_index}
        )

    def place(self, row, col, rack_index, joker_letter=None):
        if self.player_index is None:
            return {"error": "Pas de joueur connecté"}
        return self._safe_request('POST', '/place', json={
            "player_index": self.player_index,
            "row": row,
            "col": col,
            "rack_index": rack_index,
            "joker_letter": joker_letter
        })

    def play(self):
        if self.player_index is None:
            return {"error": "Pas de joueur connecté"}
        return self._safe_request('POST', '/play', json={
            "player_index": self.player_index
        })

    def pass_turn(self):
        if self.player_index is None:
            return {"error": "Pas de joueur connecté"}
        return self._safe_request('POST', '/pass', json={
            "player_index": self.player_index
        })

    def exchange(self, indices):
        if self.player_index is None:
            return {"error": "Pas de joueur connecté"}
        return self._safe_request('POST', '/exchange', json={
            "player_index": self.player_index,
            "indices": indices
        })

    def cancel(self):
        if self.player_index is None:
            return {"error": "Pas de joueur connecté"}
        return self._safe_request('POST', '/cancel', json={
            "player_index": self.player_index
        })

    def leave(self):
        """Prévient le serveur qu'on quitte (appelé à la fermeture de la fenêtre)."""
        if self.player_index is None:
            return {"error": "Pas de joueur connecté"}
        return self._safe_request('POST', '/leave', json={
            "player_index": self.player_index
        })


# ============================================================
# ÉCRAN D'ATTENTE POUR RENDER
# ============================================================

class WaitingScreen:
    def __init__(self, root, client, name, max_players):
        self.root = root
        self.client = client
        self.name = name
        self.max_players = max_players
        self.running = True

        self.root.title("Scrabble - En attente")
        self.root.geometry("500x450")
        self.root.resizable(False, False)
        self.root.configure(bg="#1f2937")

        self.frame = tk.Frame(self.root, bg="#1f2937")
        self.frame.pack(fill="both", expand=True)

        tk.Label(
            self.frame,
            text="⏳",
            font=("Arial", 48),
            bg="#1f2937"
        ).pack(pady=(40, 10))

        tk.Label(
            self.frame,
            text="En attente des joueurs...",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="#1f2937"
        ).pack()

        self.info_label = tk.Label(
            self.frame,
            text=f"Connecté : {name} (joueur {client.player_index + 1}/{max_players})",
            font=("Arial", 12),
            fg="#9ca3af",
            bg="#1f2937"
        )
        self.info_label.pack(pady=10)

        self.status_label = tk.Label(
            self.frame,
            text=f"En attente de {max_players - 1} autre(s) joueur(s)...",
            font=("Arial", 12),
            fg="#fcd34d",
            bg="#1f2937"
        )
        self.status_label.pack(pady=5)

        tk.Button(
            self.frame,
            text="🔄 Vérifier l'état",
            font=("Arial", 12),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            padx=20,
            pady=8,
            command=self.check_state
        ).pack(pady=20)

        self.check_state()
        self.auto_check()

        # Prévenir le serveur si l'utilisateur ferme la fenêtre pendant l'attente
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def on_close(self):
        self.running = False
        try:
            self.client.leave()
        except Exception:
            pass  # best-effort : on ferme la fenêtre même si l'appel échoue
        self.root.destroy()

    def auto_check(self):
        if not self.running:
            return
        self.check_state()
        self.root.after(2000, self.auto_check)

    def check_state(self):
        try:
            state = self.client.get_state()

            if 'error' in state:
                self.status_label.config(
                    text=f"⚠️ {state['error'][:50]}",
                    fg="#ef4444"
                )
                return

            players = state.get('players', [])
            count = len(players)

            if state.get('game_started', False):
                self.running = False
                self.status_label.config(
                    text="✅ Partie démarrée !",
                    fg="#4ade80"
                )
                self.root.after(500, self.start_game)
                return

            if count >= self.max_players:
                self.status_label.config(
                    text=f"🟢 {count}/{self.max_players} joueurs - La partie va commencer !",
                    fg="#4ade80"
                )
                self.running = False
                self.root.after(500, self.start_game)
            else:
                self.status_label.config(
                    text=f"🟡 {count}/{self.max_players} joueurs connectés - En attente...",
                    fg="#fcd34d"
                )

        except Exception as e:
            self.status_label.config(
                text=f"⚠️ Erreur : {str(e)[:40]}",
                fg="#ef4444"
            )

    def start_game(self):
        try:
            self.frame.destroy()
            from network_game import NetworkGame
            NetworkGame(self.root, self.client, self.name)
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Impossible de lancer le jeu :\n\n{e}"
            )
            self.root.destroy()


# ============================================================
# ÉCRAN DE CONNEXION RENDER AVEC CHOIX DU NOMBRE DE JOUEURS
# ============================================================

class RenderConnector:
    def __init__(self, root):
        self.root = root
        self.root.title("Scrabble - Connexion Render")
        self.root.geometry("420x380")
        self.root.resizable(False, False)
        self.root.configure(bg="#1f2937")

        # Titre
        tk.Label(
            self.root,
            text="☁️ CONNEXION AU SERVEUR",
            font=("Arial", 18, "bold"),
            fg="white",
            bg="#1f2937"
        ).pack(pady=(20, 5))

        tk.Label(
            self.root,
            text="Scrabble en ligne",
            font=("Arial", 12),
            fg="#9ca3af",
            bg="#1f2937"
        ).pack(pady=(0, 15))

        # Nom
        tk.Label(
            self.root,
            text="Votre nom",
            font=("Arial", 12),
            fg="white",
            bg="#1f2937"
        ).pack()

        self.name_entry = tk.Entry(
            self.root,
            font=("Arial", 14),
            justify="center",
            width=25
        )
        self.name_entry.insert(0, "Joueur")
        self.name_entry.pack(pady=5)

        # Nombre de joueurs
        tk.Label(
            self.root,
            text="Nombre de joueurs",
            font=("Arial", 12),
            fg="white",
            bg="#1f2937"
        ).pack(pady=(15, 5))

        self.max_players_var = tk.StringVar(value="2")
        self.game_already_configured = False

        # Zone dynamique : contiendra soit les boutons radio, soit un message fixe
        self.players_zone = tk.Frame(self.root, bg="#1f2937")
        self.players_zone.pack(pady=5)

        self.checking_label = tk.Label(
            self.players_zone,
            text="🔄 Vérification du serveur...",
            font=("Arial", 11, "italic"),
            fg="#9ca3af",
            bg="#1f2937"
        )
        self.checking_label.pack()

        self.connect_button = tk.Button(
            self.root,
            text="🔗 SE CONNECTER",
            font=("Arial", 14, "bold"),
            bg="#8b5cf6",
            fg="white",
            activebackground="#7c3aed",
            activeforeground="white",
            padx=30,
            pady=10,
            state="disabled",
            command=self.connect
        )
        self.connect_button.pack(pady=20)

        # Status
        self.status_label = tk.Label(
            self.root,
            text="Prêt à se connecter",
            font=("Arial", 10),
            fg="#6b7280",
            bg="#1f2937"
        )
        self.status_label.pack()

        # Vérification de l'état du serveur en arrière-plan
        # (évite de geler la fenêtre pendant le réveil de Render, ~30-50s)
        self._render_url = "https://scrabble-ml89.onrender.com"
        threading.Thread(target=self._check_server_state, daemon=True).start()

    def _check_server_state(self):
        """Exécuté dans un thread séparé : consulte /status sans bloquer l'UI."""
        client = ScrabbleClient(self._render_url)
        result = client.get_status()
        # On revient sur le thread principal Tkinter pour manipuler les widgets
        self.root.after(0, lambda: self._apply_server_state(result))

    def _apply_server_state(self, result):
        # Nettoyer la zone dynamique (retire le "Vérification...")
        for widget in self.players_zone.winfo_children():
            widget.destroy()

        if 'error' in result:
            # Serveur injoignable / en train de se réveiller : on retombe
            # sur le comportement par défaut (sélecteur libre)
            self._show_player_selector()
            self.status_label.config(
                text="⚠️ Serveur injoignable, choix libre du nombre de joueurs",
                fg="#fcd34d"
            )
            self.connect_button.config(state="normal")
            return

        configured = result.get('configured', False)
        players_count = result.get('players_count', 0)
        max_players = result.get('max_players', 4)
        game_started = result.get('game_started', False)

        if game_started:
            tk.Label(
                self.players_zone,
                text="🔴 Une partie est déjà en cours sur ce serveur.",
                font=("Arial", 11),
                fg="#ef4444",
                bg="#1f2937",
                wraplength=350
            ).pack()
            self.connect_button.config(state="disabled")
        elif configured:
            # Un premier joueur a déjà fixé le nombre de joueurs :
            # on ne propose plus le choix, on l'impose.
            self.game_already_configured = True
            self.max_players_var.set(str(max_players))
            tk.Label(
                self.players_zone,
                text=f"🔒 Partie configurée pour {max_players} joueurs\n"
                     f"({players_count}/{max_players} déjà connecté·s)",
                font=("Arial", 12, "bold"),
                fg="#4ade80",
                bg="#1f2937",
                justify="center"
            ).pack()
            self.connect_button.config(state="normal")
        else:
            # Aucune partie en cours : le premier joueur choisit
            self._show_player_selector()
            self.connect_button.config(state="normal")

    def _show_player_selector(self):
        frame_players = tk.Frame(self.players_zone, bg="#1f2937")
        frame_players.pack()

        for i, value in enumerate(["2", "3", "4"]):
            tk.Radiobutton(
                frame_players,
                text=f"{value} joueurs",
                variable=self.max_players_var,
                value=value,
                font=("Arial", 12),
                fg="white",
                bg="#1f2937",
                selectcolor="#1f2937",
                activebackground="#1f2937",
                activeforeground="white"
            ).grid(row=0, column=i, padx=15)

    def connect(self):
        name = self.name_entry.get().strip() or "Joueur"
        try:
            max_players = int(self.max_players_var.get())
        except ValueError:
            max_players = 2

        render_url = self._render_url

        self.status_label.config(text="🔄 Connexion en cours...", fg="#fcd34d")
        self.root.update()

        try:
            client = ScrabbleClient(render_url)
            result = client.join(name, max_players)

            if 'error' in result:
                self.status_label.config(
                    text=f"❌ {result['error'][:40]}...",
                    fg="#ef4444"
                )
                messagebox.showerror(
                    "Connexion",
                    f"Erreur : {result['error']}\n\n"
                    "💡 Astuces :\n"
                    "• Le serveur gratuit peut mettre 30-50s à se réveiller\n"
                    "• Vérifiez votre connexion Internet\n"
                    f"• Accédez à {render_url} dans votre navigateur"
                )
                return

            self.status_label.config(
                text=f"✅ Connecté ! (joueur {client.player_index + 1}/{max_players})",
                fg="#4ade80"
            )

            self.root.destroy()
            waiting_root = tk.Tk()
            WaitingScreen(waiting_root, client, name, max_players)
            waiting_root.mainloop()

        except Exception as e:
            self.status_label.config(text="❌ Erreur de connexion", fg="#ef4444")
            messagebox.showerror(
                "Erreur",
                f"Impossible de se connecter :\n\n{e}"
            )


# ============================================================
# MAIN
# ============================================================

def main():
    root = tk.Tk()
    RenderConnector(root)
    root.mainloop()


if __name__ == "__main__":
    main()
