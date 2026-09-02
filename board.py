BOARD_SIZE = 15

EMPTY = None


class Board:

    def __init__(self):

        self.grid = [
            [None for _ in range(BOARD_SIZE)]
            for _ in range(BOARD_SIZE)
        ]

        self.multipliers = self.create_multipliers()

        # Une case bonus ne fonctionne qu'une seule fois.
        self.used_multipliers = set()

    def create_multipliers(self):

        board = [
            [None for _ in range(BOARD_SIZE)]
            for _ in range(BOARD_SIZE)
        ]

        TW = [
            (0, 0), (0, 7), (0, 14),
            (7, 0), (7, 14),
            (14, 0), (14, 7), (14, 14)
        ]

        DW = [
            (1, 1), (2, 2), (3, 3),
            (4, 4), (10, 10), (11, 11),
            (12, 12), (13, 13),

            (1, 13), (2, 12), (3, 11),
            (4, 10), (10, 4), (11, 3),
            (12, 2), (13, 1),

            (7, 7)
        ]

        TL = [
            (1, 5), (1, 9),
            (5, 1), (5, 5), (5, 9), (5, 13),
            (9, 1), (9, 5), (9, 9), (9, 13),
            (13, 5), (13, 9)
        ]

        DL = [
            (0, 3), (0, 11),
            (2, 6), (2, 8),
            (3, 0), (3, 7), (3, 14),
            (6, 2), (6, 6), (6, 8), (6, 12),
            (7, 3), (7, 11),
            (8, 2), (8, 6), (8, 8), (8, 12),
            (11, 0), (11, 7), (11, 14),
            (12, 6), (12, 8),
            (14, 3), (14, 11)
        ]

        for r, c in TW:
            board[r][c] = "TW"

        for r, c in DW:
            board[r][c] = "DW"

        for r, c in TL:
            board[r][c] = "TL"

        for r, c in DL:
            board[r][c] = "DL"

        return board

    def get(self, row, column):
        return self.grid[row][column]

    def set(self, row, column, value):
        self.grid[row][column] = value

    def is_empty(self):
        return all(
            cell is None
            for row in self.grid
            for cell in row
        )

    def multiplier_at(self, row, column):

        if (row, column) in self.used_multipliers:
            return None

        return self.multipliers[row][column]

    def consume_multipliers(self, positions):

        for position in positions:
            if self.multipliers[
                position[0]
            ][
                position[1]
            ] is not None:

                self.used_multipliers.add(position)

    def inside(self, row, column):
        return (
            0 <= row < BOARD_SIZE
            and
            0 <= column < BOARD_SIZE
        )

    def neighbours(self, row, column):

        directions = [
            (-1, 0),
            (1, 0),
            (0, -1),
            (0, 1)
        ]

        result = []

        for dr, dc in directions:

            r = row + dr
            c = column + dc

            if self.inside(r, c):
                result.append((r, c))

        return result