import os
import unicodedata


DICTIONARY_FILE = os.path.join(
    os.path.dirname(__file__),
    "mots.txt"
)


def normalize_word(word):
    word = word.strip().upper()

    # Suppression des accents
    word = unicodedata.normalize("NFD", word)

    word = "".join(
        char
        for char in word
        if unicodedata.category(char) != "Mn"
    )

    return word


class ScrabbleDictionary:

    def __init__(self, filename=DICTIONARY_FILE):
        self.filename = filename
        self.words = set()

        self.load()

    def load(self):

        if not os.path.exists(self.filename):
            raise FileNotFoundError(
                f"Dictionnaire introuvable : {self.filename}"
            )

        with open(
            self.filename,
            "r",
            encoding="utf-8"
        ) as file:

            for line in file:

                word = normalize_word(line)

                if not word:
                    continue

                # Scrabble = uniquement A-Z
                if word.isalpha():
                    self.words.add(word)

        print(
            f"Dictionnaire chargé : "
            f"{len(self.words):,} mots"
        )

    def contains(self, word):
        return normalize_word(word) in self.words

    def __contains__(self, word):
        return self.contains(word)


dictionary = ScrabbleDictionary()