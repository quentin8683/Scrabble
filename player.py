class Player:

    def __init__(self, name):
        self.name = name
        self.score = 0
        self.rack = []

    def add_score(self, points):
        self.score += points

    def remove_tiles(self, tiles):
        """
        Retire les tuiles données du chevalet.
        """

        rack = self.rack.copy()

        for tile in tiles:
            if tile not in rack:
                return False

            rack.remove(tile)

        self.rack = rack

        return True

    def can_make(self, letters):
        """
        Vérifie si les lettres peuvent être fabriquées
        avec le chevalet, en utilisant éventuellement les jokers.
        """

        rack = self.rack.copy()

        for letter in letters:
            if letter in rack:
                rack.remove(letter)

            elif "?" in rack:
                rack.remove("?")

            else:
                return False

        return True