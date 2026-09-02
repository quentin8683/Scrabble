import json
import socket
import threading

from board import Board
from player import Player
from tiles import TileBag, TILE_VALUES
from dictionary import dictionary


class GameEngine:
    """
    Moteur de jeu Scrabble côté serveur.

    Le serveur est autoritaire :
    - plateau
    - sac
    - chevalets
    - scores
    - tour actuel
    - validation des mots
    """

    def __init__(self, player_names):

        self.board = Board()
        self.tile_bag = TileBag()

        self.players = [
            Player(name)
            for name in player_names
        ]

        self.current_player = 0

        # Tuiles posées temporairement pendant le tour
        self.pending = []

        # Nombre de passes successives
        self.consecutive_passes = 0

        # Distribution initiale
        for player in self.players:
            player.rack = self.tile_bag.draw_multiple(7)

    # =========================================================
    # ETAT DU JEU
    # =========================================================

    def state(self):

        return {
            "board": self.board.grid,

            "used_multipliers": [
                list(position)
                for position in self.board.used_multipliers
            ],

            "players": [
                {
                    "name": player.name,
                    "score": player.score,
                    "rack_count": len(player.rack)
                }
                for player in self.players
            ],

            "current_player": self.current_player,

            "remaining": self.tile_bag.remaining(),

            # Les placements temporaires sont visibles par tous.
            "pending": [
                {
                    "row": p["row"],
                    "col": p["col"],
                    "letter": p["letter"]
                }
                for p in self.pending
            ]
        }

    def private_state(self, player_index):

        game_state = self.state()

        # Chaque joueur reçoit uniquement SON chevalet.
        game_state["rack"] = list(
            self.players[player_index].rack
        )

        return game_state

    # =========================================================
    # LETTRES / MOTS
    # =========================================================

    def get_letter(self, row, col):

        # Chercher d'abord dans les tuiles temporaires
        for p in self.pending:

            if (
                p["row"] == row
                and
                p["col"] == col
            ):
                return p["letter"]

        # Puis dans le plateau définitif
        value = self.board.get(row, col)

        if value is None:
            return None

        if isinstance(value, tuple):
            return value[0]

        return value

    def build_word(
        self,
        row,
        col,
        dr,
        dc
    ):

        # Remonter jusqu'au début du mot
        r = row
        c = col

        while (
            self.board.inside(
                r - dr,
                c - dc
            )
            and
            self.get_letter(
                r - dr,
                c - dc
            ) is not None
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

    # =========================================================
    # VALIDATION DU PLACEMENT
    # =========================================================

    def validate_placement(self):

        if not self.pending:

            return (
                False,
                "Aucune lettre posée."
            )

        positions = [
            (p["row"], p["col"])
            for p in self.pending
        ]

        # -----------------------------------------------------
        # UNE SEULE LETTRE
        # -----------------------------------------------------

        if len(positions) == 1:

            r, c = positions[0]

            # Premier coup
            if self.board.is_empty():

                if (r, c) != (7, 7):

                    return (
                        False,
                        "Le premier mot doit passer par le centre."
                    )

            # Partie déjà commencée
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

        # -----------------------------------------------------
        # ALIGNEMENT
        # -----------------------------------------------------

        rows = {
            p[0]
            for p in positions
        }

        cols = {
            p[1]
            for p in positions
        }

        if (
            len(rows) != 1
            and
            len(cols) != 1
        ):

            return (
                False,
                "Les lettres doivent être alignées."
            )

        # -----------------------------------------------------
        # HORIZONTAL
        # -----------------------------------------------------

        if len(rows) == 1:

            row = next(iter(rows))

            sorted_positions = sorted(
                positions,
                key=lambda p: p[1]
            )

            start = sorted_positions[0][1]
            end = sorted_positions[-1][1]

            for col in range(
                start,
                end + 1
            ):

                if (
                    self.board.get(row, col) is None
                    and
                    (row, col) not in positions
                ):

                    return (
                        False,
                        "Le mot ne peut pas contenir de trou."
                    )

        # -----------------------------------------------------
        # VERTICAL
        # -----------------------------------------------------

        else:

            col = next(iter(cols))

            sorted_positions = sorted(
                positions,
                key=lambda p: p[0]
            )

            start = sorted_positions[0][0]
            end = sorted_positions[-1][0]

            for row in range(
                start,
                end + 1
            ):

                if (
                    self.board.get(row, col) is None
                    and
                    (row, col) not in positions
                ):

                    return (
                        False,
                        "Le mot ne peut pas contenir de trou."
                    )

        # -----------------------------------------------------
        # CONNEXION AU PLATEAU
        # -----------------------------------------------------

        if self.board.is_empty():

            if (7, 7) not in positions:

                return (
                    False,
                    "Le premier mot doit passer par la case centrale."
                )

        else:

            connected = False

            for r, c in positions:

                for nr, nc in self.board.neighbours(
                    r,
                    c
                ):

                    if self.board.get(
                        nr,
                        nc
                    ) is not None:

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
    # DETECTION DES MOTS
    # =========================================================

    def find_words(self):

        words = []
        seen = set()

        for pending_tile in self.pending:

            row = pending_tile["row"]
            col = pending_tile["col"]

            # Horizontal
            word, positions = self.build_word(
                row,
                col,
                0,
                1
            )

            if len(word) >= 2:

                key = (
                    "horizontal",
                    tuple(positions)
                )

                if key not in seen:

                    seen.add(key)

                    words.append(
                        (
                            "horizontal",
                            word,
                            positions
                        )
                    )

            # Vertical
            word, positions = self.build_word(
                row,
                col,
                1,
                0
            )

            if len(word) >= 2:

                key = (
                    "vertical",
                    tuple(positions)
                )

                if key not in seen:

                    seen.add(key)

                    words.append(
                        (
                            "vertical",
                            word,
                            positions
                        )
                    )

        return words

    # =========================================================
    # SCORE
    # =========================================================

    def score_word(
        self,
        word,
        positions
    ):

        total = 0
        word_multiplier = 1

        for letter, (row, col) in zip(
            word,
            positions
        ):

            value = TILE_VALUES.get(
                letter,
                0
            )

            pending_tile = next(
                (
                    p
                    for p in self.pending
                    if (
                        p["row"] == row
                        and
                        p["col"] == col
                    )
                ),
                None
            )

            # Bonus uniquement sur les nouvelles tuiles
            if pending_tile is not None:

                multiplier = self.board.multiplier_at(
                    row,
                    col
                )

                if multiplier == "DL":
                    value *= 2

                elif multiplier == "TL":
                    value *= 3

                elif multiplier == "DW":
                    word_multiplier *= 2

                elif multiplier == "TW":
                    word_multiplier *= 3

                # Joker = 0 point
                if pending_tile["tile"] == "?":
                    value = 0

            total += value

        return total * word_multiplier

    # =========================================================
    # POSER UNE TUILE
    # =========================================================

    def place(
        self,
        player_index,
        row,
        col,
        rack_index,
        joker_letter=None
    ):

        # Vérification du tour
        if player_index != self.current_player:

            return (
                False,
                "Ce n'est pas votre tour."
            )

        # Vérification de la case
        if not self.board.inside(
            row,
            col
        ):

            return (
                False,
                "Case invalide."
            )

        if self.board.get(
            row,
            col
        ) is not None:

            return (
                False,
                "Cette case est déjà occupée."
            )

        # Vérification doublon temporaire
        for p in self.pending:

            if (
                p["row"] == row
                and
                p["col"] == col
            ):

                return (
                    False,
                    "Cette case est déjà sélectionnée."
                )

        player = self.players[player_index]

        # Vérification du chevalet
        if (
            rack_index < 0
            or
            rack_index >= len(player.rack)
        ):

            return (
                False,
                "Tuile invalide."
            )

        tile = player.rack[rack_index]

        # -----------------------------------------------------
        # JOKER
        # -----------------------------------------------------

        if tile == "?":

            if (
                not joker_letter
                or
                len(joker_letter) != 1
                or
                not joker_letter.isalpha()
            ):

                return (
                    False,
                    "Le joker doit représenter une lettre."
                )

            letter = joker_letter.upper()

        else:

            letter = tile

        # -----------------------------------------------------
        # PLACEMENT TEMPORAIRE
        # -----------------------------------------------------

        self.pending.append(
            {
                "row": row,
                "col": col,
                "letter": letter,
                "tile": tile,
                "rack_index": rack_index
            }
        )

        return True, ""

    # =========================================================
    # ANNULER
    # =========================================================

    def cancel(
        self,
        player_index
    ):

        if player_index != self.current_player:

            return (
                False,
                "Ce n'est pas votre tour."
            )

        self.pending.clear()

        return True, ""

    # =========================================================
    # JOUER LE MOT
    # =========================================================

    def play(
        self,
        player_index
    ):

        if player_index != self.current_player:

            return (
                False,
                "Ce n'est pas votre tour."
            )

        # Validation
        valid, error = self.validate_placement()

        if not valid:
            return False, error

        # Recherche des mots
        words = self.find_words()

        if not words:

            return (
                False,
                "Aucun mot valide n'a été créé."
            )

        # Dictionnaire
        for _, word, _ in words:

            if word not in dictionary:

                return (
                    False,
                    f"« {word} » n'est pas autorisé."
                )

        # -----------------------------------------------------
        # CALCUL DU SCORE
        # -----------------------------------------------------

        total_score = 0

        for _, word, positions in words:

            total_score += self.score_word(
                word,
                positions
            )

        # Scrabble
        if len(self.pending) == 7:
            total_score += 50

        player = self.players[player_index]

        # -----------------------------------------------------
        # TRANSFORMATION EN PLACEMENT DEFINITIF
        # -----------------------------------------------------

        positions = []

        for p in self.pending:

            self.board.set(
                p["row"],
                p["col"],
                p["letter"]
            )

            positions.append(
                (
                    p["row"],
                    p["col"]
                )
            )

        # Consommer les bonus
        self.board.consume_multipliers(
            positions
        )

        # -----------------------------------------------------
        # RETIRER LES TUILES DU CHEVALET
        # -----------------------------------------------------

        for p in sorted(
            self.pending,
            key=lambda x: x["rack_index"],
            reverse=True
        ):

            player.rack.pop(
                p["rack_index"]
            )

        # Score
        player.add_score(
            total_score
        )

        # Nettoyage
        self.pending.clear()

        # Remplissage du chevalet
        while len(player.rack) < 7:

            tile = self.tile_bag.draw()

            if tile is None:
                break

            player.rack.append(tile)

        self.consecutive_passes = 0

        result = {
            "score": total_score,
            "words": [
                word
                for _, word, _ in words
            ]
        }

        # -----------------------------------------------------
        # FIN DE PARTIE
        # -----------------------------------------------------

        if (
            len(player.rack) == 0
            and
            self.tile_bag.remaining() == 0
        ):

            result["game_over"] = self.finish()

            return True, result

        # Tour suivant
        self.next_turn()

        return True, result

    # =========================================================
    # PASSER
    # =========================================================

    def pass_turn(
        self,
        player_index
    ):

        if player_index != self.current_player:

            return (
                False,
                "Ce n'est pas votre tour."
            )

        self.pending.clear()

        self.consecutive_passes += 1

        if (
            self.consecutive_passes
            >=
            len(self.players) * 2
        ):

            return True, {
                "game_over": self.finish()
            }

        self.next_turn()

        return True, {}

    # =========================================================
    # ECHANGE
    # =========================================================

    def exchange(
        self,
        player_index,
        indices
    ):

        if player_index != self.current_player:

            return (
                False,
                "Ce n'est pas votre tour."
            )

        if self.pending:

            return (
                False,
                "Annulez d'abord votre placement."
            )

        if not indices:

            return (
                False,
                "Aucune tuile sélectionnée."
            )

        if self.tile_bag.remaining() < len(indices):

            return (
                False,
                "Pas assez de lettres dans le sac."
            )

        player = self.players[player_index]

        indices = sorted(
            set(indices),
            reverse=True
        )

        if any(
            i < 0
            or
            i >= len(player.rack)
            for i in indices
        ):

            return (
                False,
                "Position de tuile invalide."
            )

        old_tiles = [
            player.rack[i]
            for i in indices
        ]

        # Retirer les anciennes
        for index in indices:

            player.rack.pop(index)

        # Tirer les nouvelles
        new_tiles = self.tile_bag.draw_multiple(
            len(old_tiles)
        )

        player.rack.extend(
            new_tiles
        )

        # Remettre les anciennes dans le sac
        self.tile_bag.put_back(
            old_tiles
        )

        self.consecutive_passes = 0

        self.next_turn()

        return True, {}

    # =========================================================
    # TOUR SUIVANT
    # =========================================================

    def next_turn(self):

        self.current_player += 1

        if (
            self.current_player
            >=
            len(self.players)
        ):

            self.current_player = 0

    # =========================================================
    # FIN DE PARTIE
    # =========================================================

    def finish(self):

        # Retirer les points des lettres restantes
        for player in self.players:

            penalty = sum(
                TILE_VALUES[tile]
                for tile in player.rack
            )

            player.score -= penalty

        ranking = sorted(
            [
                {
                    "name": player.name,
                    "score": player.score
                }
                for player in self.players
            ],
            key=lambda p: p["score"],
            reverse=True
        )

        return ranking


# =============================================================
# SERVEUR
# =============================================================

class ScrabbleServer:

    def __init__(
        self,
        host="0.0.0.0",
        port=5050,
        max_players=4
    ):

        self.host = host
        self.port = port
        self.max_players = max_players

        self.server_socket = None

        self.clients = {}

        self.names = []

        self.engine = None

        self.started = False

        self.lock = threading.RLock()

    # =========================================================
    # ENVOI
    # =========================================================

    def send(
        self,
        connection,
        data
    ):

        message = (
            json.dumps(
                data,
                ensure_ascii=False
            )
            + "\n"
        )

        connection.sendall(
            message.encode("utf-8")
        )

    # =========================================================
    # BROADCAST
    # =========================================================

    def broadcast(
        self,
        data
    ):

        for connection in list(
            self.clients.keys()
        ):

            try:

                self.send(
                    connection,
                    data
                )

            except OSError:

                pass

    # =========================================================
    # ENVOYER L'ETAT A TOUS
    # =========================================================

    def broadcast_states(self):

        if self.engine is None:
            return

        for connection, player_index in list(
            self.clients.items()
        ):

            try:

                self.send(
                    connection,
                    {
                        "type": "state",
                        "state":
                            self.engine.private_state(
                                player_index
                            )
                    }
                )

            except OSError:

                pass

    # =========================================================
    # CLIENT
    # =========================================================

    def handle_client(
        self,
        connection,
        address
    ):

        player_index = None

        try:

            file = connection.makefile(
                "r",
                encoding="utf-8"
            )

            # -------------------------------------------------
            # PREMIER MESSAGE = JOIN
            # -------------------------------------------------

            first_line = file.readline()

            if not first_line:

                return

            first_message = json.loads(
                first_line
            )

            if first_message.get(
                "type"
            ) != "join":

                self.send(
                    connection,
                    {
                        "type": "error",
                        "message":
                            "Connexion invalide."
                    }
                )

                return

            name = str(
                first_message.get(
                    "name",
                    ""
                )
            ).strip()

            if not name:
                name = "Joueur"

            name = name[:30]

            # -------------------------------------------------
            # AJOUT DU JOUEUR
            # -------------------------------------------------

            with self.lock:

                if self.started:

                    self.send(
                        connection,
                        {
                            "type": "error",
                            "message":
                                "La partie a déjà commencé."
                        }
                    )

                    return

                if len(self.clients) >= self.max_players:

                    self.send(
                        connection,
                        {
                            "type": "error",
                            "message":
                                "La partie est complète."
                        }
                    )

                    return

                player_index = len(
                    self.clients
                )

                self.clients[
                    connection
                ] = player_index

                self.names.append(
                    name
                )

                self.send(
                    connection,
                    {
                        "type": "joined",
                        "player_index":
                            player_index
                    }
                )

                print(
                    f"[+] {name} connecté "
                    f"depuis {address}"
                )

                # -------------------------------------------------
                # DEMARRAGE A 2 JOUEURS
                # -------------------------------------------------

                if len(self.clients) >= 2:

                    self.engine = GameEngine(
                        self.names
                    )

                    self.started = True

                    print(
                        "=== PARTIE DEMARREE ==="
                    )

                    self.broadcast(
                        {
                            "type":
                                "started"
                        }
                    )

                    self.broadcast_states()

                else:

                    self.send(
                        connection,
                        {
                            "type":
                                "info",
                            "message":
                                "En attente d'un autre joueur..."
                        }
                    )

            # -------------------------------------------------
            # BOUCLE DES ACTIONS
            # -------------------------------------------------

            for line in file:

                if not line.strip():
                    continue

                message = json.loads(
                    line
                )

                with self.lock:

                    if (
                        not self.started
                        or
                        self.engine is None
                    ):

                        self.send(
                            connection,
                            {
                                "type":
                                    "info",
                                "message":
                                    "En attente d'autres joueurs..."
                            }
                        )

                        continue

                    success, result = (
                        self.apply_action(
                            player_index,
                            message
                        )
                    )

                    if success:

                        self.broadcast_states()

                        if (
                            isinstance(
                                result,
                                dict
                            )
                            and
                            "game_over"
                            in result
                        ):

                            self.broadcast(
                                {
                                    "type":
                                        "game_over",
                                    "ranking":
                                        result[
                                            "game_over"
                                        ]
                                }
                            )

                    else:

                        self.send(
                            connection,
                            {
                                "type":
                                    "error",
                                "message":
                                    result
                            }
                        )

        except (
            ConnectionError,
            OSError,
            json.JSONDecodeError,
            ValueError,
            KeyError
        ):

            print(
                f"[-] Connexion perdue : "
                f"{address}"
            )

        finally:

            with self.lock:

                if connection in self.clients:

                    del self.clients[
                        connection
                    ]

            try:
                connection.close()
            except OSError:
                pass

    # =========================================================
    # ACTION
    # =========================================================

    def apply_action(
        self,
        player_index,
        message
    ):

        action = message.get(
            "type"
        )

        if action == "place":

            return self.engine.place(
                player_index,
                int(message["row"]),
                int(message["col"]),
                int(message["rack_index"]),
                message.get("joker")
            )

        if action == "cancel":

            return self.engine.cancel(
                player_index
            )

        if action == "play":

            return self.engine.play(
                player_index
            )

        if action == "pass":

            return self.engine.pass_turn(
                player_index
            )

        if action == "exchange":

            indices = [
                int(index)
                for index in message.get(
                    "indices",
                    []
                )
            ]

            return self.engine.exchange(
                player_index,
                indices
            )

        return (
            False,
            "Action inconnue."
        )

    # =========================================================
    # DEMARRAGE DU SERVEUR
    # =========================================================

    def run(self):

        self.server_socket = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        self.server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        self.server_socket.bind(
            (
                self.host,
                self.port
            )
        )

        self.server_socket.listen(
            8
        )

        print()
        print(
            "=================================="
        )
        print(
            "       SCRABBLE - SERVEUR"
        )
        print(
            "=================================="
        )
        print(
            f"Port : {self.port}"
        )
        print(
            "En attente des joueurs..."
        )
        print()

        while True:

            connection, address = (
                self.server_socket.accept()
            )

            thread = threading.Thread(
                target=self.handle_client,
                args=(
                    connection,
                    address
                ),
                daemon=True
            )

            thread.start()


# =============================================================
# LANCEMENT DIRECT DU SERVEUR
# =============================================================

if __name__ == "__main__":

    import argparse

    parser = argparse.ArgumentParser(
        description="Serveur Scrabble"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=5050
    )

    args = parser.parse_args()

    server = ScrabbleServer(
        port=args.port
    )

    server.run()