# Scrabble réseau d'entreprise

## 1. Installer / préparer
Placez tous les fichiers `.py` ensemble, ainsi que `mots.txt`.

Fichiers ajoutés :
- `network_server.py` : serveur autoritaire
- `network_game.py` : interface cliente
- `main_network.py` : écran de connexion

Les fichiers originaux `board.py`, `dictionary.py`, `game.py`, `main.py`, `player.py` et `tiles.py` restent utilisables pour la version locale.

## 2. Sur le PC qui héberge la partie

Ouvrir un terminal dans le dossier du jeu :

```bash
python network_server.py
```

Le port par défaut est `5050`.

Trouver l'adresse IP du PC serveur :
- Windows : `ipconfig`
- Linux/macOS : `ip addr` ou `ifconfig`

Par exemple : `192.168.1.42`.

## 3. Sur chaque PC joueur

Lancer :

```bash
python main_network.py
```

Saisir :
- son nom ;
- l'IP du PC serveur, par exemple `192.168.1.42` ;
- le port `5050`.

Au moins 2 joueurs doivent se connecter. Le serveur accepte jusqu'à 4 joueurs.

## 4. Pare-feu Windows

Sur le PC serveur, autoriser Python sur le réseau privé, ou ouvrir le port TCP 5050 dans le pare-feu Windows.

## Architecture

Le serveur est autoritaire : le plateau, le sac, les chevalets, les scores, les tours,
la validation des mots et les échanges sont gérés côté serveur. Les clients ne font
qu'envoyer leurs actions et afficher l'état reçu.

Le dictionnaire reste celui du projet existant (`mots.txt` via `dictionary.py`).
