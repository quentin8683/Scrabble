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
            # Ajouter le Content-Type si ce n'est pas déjà fait
            if 'headers' not in kwargs:
                kwargs['headers'] = {}
            kwargs['headers']['Content-Type'] = 'application/json'
            
            response = requests.request(method, url, verify=False, timeout=60, **kwargs)
            
            # Vérifier le statut
            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}"}
            
            # Vérifier que c'est du JSON
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

    def join(self, name):
        result = self._safe_request('POST', '/join', json={"name": name})
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


# ============================================================
# ÉCRAN D'ATTENTE POUR RENDER (CORRIGÉ)
# ============================================================

class WaitingScreen:
    def __init__(self, root, client, name):
        self.root = root
        self.client = client
        self.name = name
        self.running = True
        
        self.root.title("Scrabble - En attente")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        self.root.configure(bg="#1f2937")
        
        # Interface
        self.frame = tk.Frame(self.root, bg="#1f2937")
        self.frame.pack(fill="both", expand=True)
        
        # Icône d'attente
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
        
        # Informations
        self.info_label = tk.Label(
            self.frame,
            text=f"Connecté : {name} (joueur {client.player_index + 1})",
            font=("Arial", 12),
            fg="#9ca3af",
            bg="#1f2937"
        )
        self.info_label.pack(pady=10)
        
        self.status_label = tk.Label(
            self.frame,
            text="En attente d'un autre joueur...",
            font=("Arial", 12),
            fg="#fcd34d",
            bg="#1f2937"
        )
        self.status_label.pack(pady=5)
        
        # Bouton pour vérifier manuellement
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
        
        # Démarrer la vérification automatique
        self.check_state()
        self.auto_check()

    def auto_check(self):
        """Vérifie l'état toutes les 2 secondes"""
        if not self.running:
            return
        self.check_state()
        self.root.after(2000, self.auto_check)

    def check_state(self):
        """Vérifie si la partie a démarré"""
        try:
            state = self.client.get_state()
            
            if 'error' in state:
                self.status_label.config(
                    text=f"⚠️ {state['error'][:50]}",
                    fg="#ef4444"
                )
                return
            
            # 🔍 AFFICHER L'ÉTAT POUR DÉBOGUER
            print(f"État reçu : game_started={state.get('game_started')}, players={state.get('players')}")
            
            # Récupérer le nombre de joueurs
            players = state.get('players', [])
            count = len(players)
            
            # ✅ DÉMARRER LA PARTIE DÈS QUE 2 JOUEURS SONT CONNECTÉS
            if count >= 2:
                self.status_label.config(
                    text=f"🟢 {count} joueurs connectés - Lancement de la partie !",
                    fg="#4ade80"
                )
                self.running = False
                self.root.after(500, self.start_game)
                return
            
            if count == 1:
                self.status_label.config(
                    text="🟡 1 joueur connecté - En attente d'un adversaire...",
                    fg="#fcd34d"
                )
            else:
                self.status_label.config(
                    text="🟡 En attente d'autres joueurs...",
                    fg="#fcd34d"
                )
                
        except Exception as e:
            self.status_label.config(
                text=f"⚠️ Erreur : {str(e)[:40]}",
                fg="#ef4444"
            )

    def start_game(self):
        """Lance l'interface de jeu"""
        try:
            self.frame.destroy()
            # Importer NetworkGame
            from network_game import NetworkGame
            NetworkGame(self.root, self.client, self.name)
        except Exception as e:
            messagebox.showerror(
                "Erreur",
                f"Impossible de lancer le jeu :\n\n{e}"
            )
            self.root.destroy()


# ============================================================
# ÉCRAN DE CONNEXION RENDER
# ============================================================

class RenderConnector:
    def __init__(self, root):
        self.root = root
        self.root.title("Scrabble - Connexion Render")
        self.root.geometry("400x300")
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
        ).pack(pady=(0, 20))
        
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
        
        # Bouton
        tk.Button(
            self.root,
            text="🔗 SE CONNECTER",
            font=("Arial", 14, "bold"),
            bg="#8b5cf6",
            fg="white",
            activebackground="#7c3aed",
            activeforeground="white",
            padx=30,
            pady=10,
            command=self.connect
        ).pack(pady=20)
        
        # Status
        self.status_label = tk.Label(
            self.root,
            text="Prêt à se connecter",
            font=("Arial", 10),
            fg="#6b7280",
            bg="#1f2937"
        )
        self.status_label.pack()

    def connect(self):
        name = self.name_entry.get().strip() or "Joueur"
        render_url = "https://scrabble-ml89.onrender.com"
        
        self.status_label.config(text="🔄 Connexion en cours...", fg="#fcd34d")
        self.root.update()
        
        try:
            client = ScrabbleClient(render_url)
            result = client.join(name)
            
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
                text=f"✅ Connecté ! (joueur {client.player_index + 1})",
                fg="#4ade80"
            )
            
            # Passer à l'écran d'attente
            self.root.destroy()
            waiting_root = tk.Tk()
            WaitingScreen(waiting_root, client, name)
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
