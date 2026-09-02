import tkinter as tk
from tkinter import messagebox, simpledialog
from network_game import NetworkGame


class NetworkStartScreen:
    def __init__(self, root):
        self.root = root
        self.root.title("Scrabble — Réseau")
        self.root.geometry("520x500")
        self.root.resizable(False, False)
        self.frame = tk.Frame(root, bg="#1f2937")
        self.frame.pack(fill="both", expand=True)

        tk.Label(self.frame, text="SCRABBLE RÉSEAU",
                 font=("Arial", 28, "bold"), fg="white", bg="#1f2937").pack(pady=30)

        tk.Label(self.frame, text="Nom du joueur", font=("Arial", 14),
                 fg="white", bg="#1f2937").pack(pady=5)
        self.name = tk.Entry(self.frame, font=("Arial", 14), width=28)
        self.name.insert(0, "Joueur")
        self.name.pack(pady=5)

        tk.Label(self.frame, text="IP du PC serveur", font=("Arial", 14),
                 fg="white", bg="#1f2937").pack(pady=(20, 5))
        self.host = tk.Entry(self.frame, font=("Arial", 14), width=28)
        self.host.insert(0, "127.0.0.1")
        self.host.pack(pady=5)

        tk.Label(self.frame, text="Port", font=("Arial", 14),
                 fg="white", bg="#1f2937").pack(pady=(15, 5))
        self.port = tk.Entry(self.frame, font=("Arial", 14), width=10)
        self.port.insert(0, "5050")
        self.port.pack(pady=5)

        tk.Button(self.frame, text="SE CONNECTER",
                  font=("Arial", 14, "bold"), bg="#2563eb", fg="white",
                  padx=25, pady=10, command=self.start).pack(pady=25)

    def start(self):
        name = self.name.get().strip() or "Joueur"
        host = self.host.get().strip() or "127.0.0.1"
        try:
            port = int(self.port.get())
        except ValueError:
            messagebox.showerror("Réseau", "Port invalide.")
            return

        try:
            self.frame.destroy()
            NetworkGame(self.root, host, port, name)
        except RuntimeError as e:
            messagebox.showerror("Réseau", str(e))
            self.frame = tk.Frame(self.root, bg="#1f2937")
            self.frame.pack(fill="both", expand=True)
            # Recréation simple de l'écran en relançant l'application
            messagebox.showinfo("Réseau", "Relancez l'application après correction.")


def main():
    root = tk.Tk()
    NetworkStartScreen(root)
    root.mainloop()


if __name__ == "__main__":
    main()
