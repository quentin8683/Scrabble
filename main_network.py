import requests
import json

class ScrabbleClient:
    def __init__(self, server_url):
        self.server_url = server_url
        self.player_index = None
    
    def join(self, name):
        response = requests.post(
            f"{self.server_url}/join",
            json={"name": name}
        )
        data = response.json()
        self.player_index = data.get('player_index')
        return data
    
    def get_state(self):
        response = requests.get(
            f"{self.server_url}/state",
            params={"player_index": self.player_index}
        )
        return response.json()
    
    def place(self, row, col, rack_index, joker_letter=None):
        response = requests.post(
            f"{self.server_url}/place",
            json={
                "player_index": self.player_index,
                "row": row,
                "col": col,
                "rack_index": rack_index,
                "joker_letter": joker_letter
            }
        )
        return response.json()
    
    def play(self):
        response = requests.post(
            f"{self.server_url}/play",
            json={"player_index": self.player_index}
        )
        return response.json()
    
    def pass_turn(self):
        response = requests.post(
            f"{self.server_url}/pass",
            json={"player_index": self.player_index}
        )
        return response.json()
    
    def exchange(self, indices):
        response = requests.post(
            f"{self.server_url}/exchange",
            json={
                "player_index": self.player_index,
                "indices": indices
            }
        )
        return response.json()
    
    def cancel(self):
        response = requests.post(
            f"{self.server_url}/cancel",
            json={"player_index": self.player_index}
        )
        return response.json()

# ============================================================
# EXEMPLE D'UTILISATION
# ============================================================

if __name__ == "__main__":
    # URL de votre serveur Render
    SERVER_URL = "https://scrabble-ml89.onrender.com"
    
    client = ScrabbleClient(SERVER_URL)
    
    # Exemple : rejoindre la partie
    name = input("Entrez votre nom : ")
    result = client.join(name)
    print("Résultat :", result)
    
    # Exemple : voir l'état du jeu
    if client.player_index is not None:
        state = client.get_state()
        print("État du jeu :", state)
