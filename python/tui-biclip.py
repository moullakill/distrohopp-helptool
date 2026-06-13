#!/usr/bin/env python3
import sys
import socket
import threading
import time
import curses

PORT = 9999
BUFFER_SIZE = 4096
clipboard_content = "Vide"

# ==========================================
# PARTIE SERVEUR
# ==========================================
def start_central_server():
    """Gère le stockage en RAM unique."""
    global clipboard_content
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', PORT))
        server.listen(5)
    except Exception as e:
        print(f"Erreur Serveur: {e}")
        return

    while True:
        try:
            conn, addr = server.accept()
            data = conn.recv(BUFFER_SIZE).decode('utf-8')
            if data:
                if data.startswith("PUSH:"):
                    clipboard_content = data[5:]
                    conn.sendall(b"OK")
                elif data == "PULL":
                    conn.sendall(clipboard_content.encode('utf-8'))
            conn.close()
        except Exception:
            pass

def send_to_server(server_ip, message):
    """Envoie une commande rapide au serveur."""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(1.5)
        client.connect((server_ip, PORT))
        client.sendall(message.encode('utf-8'))
        res = client.recv(BUFFER_SIZE).decode('utf-8')
        client.close()
        return res
    except Exception:
        return None

# ==========================================
# PARTIE CLIENT TUI (PLEIN ÉCRAN)
# ==========================================
class TUIClient:
    def __init__(self, stdscr, server_ip):
        self.stdscr = stdscr
        self.server_ip = server_ip
        self.current_text = ""
        self.running = True
        self.input_mode = False
        
    def start(self):
        # Configuration de curses pour le plein écran et compatibilité tmux
        curses.curs_set(1) # Rendre le curseur visible
        self.stdscr.nodelay(True) # Ne pas bloquer sur getch()
        self.stdscr.keypad(True)  # Activer les touches spéciales
        
        # Lancement du thread de synchronisation en temps réel (Pull)
        threading.Thread(target=self.sync_loop, daemon=True).start()
        
        # Boucle principale de rendu et d'input
        buffer_input = ""
        while self.running:
            self.draw_ui(buffer_input)
            
            try:
                ch = self.stdscr.getch()
            except Exception:
                continue

            if ch == -1:
                time.sleep(0.05)
                continue
                
            if not self.input_mode:
                # Mode Navigation / Commandes
                if ch in (ord('q'), 27): # 'q' ou Échap pour quitter
                    self.running = False
                elif ch in (ord('i'), ord('\n')): # 'i' ou Entrée pour éditer
                    self.input_mode = True
                    buffer_input = self.current_text
            else:
                # Mode Édition (écriture)
                if ch == 27: # Échap pour annuler/sortir du mode édition
                    self.input_mode = False
                elif ch in (10, 13): # Entrée pour valider et PUSH
                    send_to_server(self.server_ip, f"PUSH:{buffer_input}")
                    self.input_mode = False
                elif ch in (curses.KEY_BACKSPACE, 127, 8): # Gérer les retours arrière
                    buffer_input = buffer_input[:-1]
                elif 32 <= ch <= 126: # Caractères imprimables
                    buffer_input += chr(ch)

    def sync_loop(self):
        """Récupère le contenu du serveur toutes les secondes si on n'édite pas."""
        while self.running:
            if not self.input_mode:
                res = send_to_server(self.server_ip, "PULL")
                if res is not None:
                    self.current_text = res
            time.sleep(1.0)

    def draw_ui(self, buffer_input):
        self.stdscr.erase()
        h, w = self.stdscr.getmaxyx()
        
        # Barre de titre supérieure (style nano)
        title = f" BICLIP TUI - Serveur: {self.server_ip} "
        self.stdscr.attron(curses.A_REVERSE)
        self.stdscr.addstr(0, 0, title.center(w)[:w-1])
        self.stdscr.attroff(curses.A_REVERSE)
        
        # Zone centrale (Affichage du texte synchro)
        self.stdscr.addstr(2, 2, "Contenu synchronisé :")
        
        if self.input_mode:
            # Affichage pendant la saisie
            self.stdscr.addstr(4, 4, buffer_input[:w-10], curses.A_BOLD)
            # Positionner le curseur au bout du texte tapé
            cursor_pos = min(4 + len(buffer_input), w - 2)
            self.stdscr.move(4, cursor_pos)
        else:
            # Affichage passif
            self.stdscr.addstr(4, 4, self.current_text[:w-10])
            self.stdscr.move(0, 0) # Cache le curseur en haut à gauche
            
        # Barre d'aide inférieure
        self.stdscr.attron(curses.A_REVERSE)
        if not self.input_mode:
            help_text = " [i] Éditer/Push  |  [q] Quitter "
        else:
            help_text = " [Entrée] Valider/Push  |  [Échap] Mode Lecture "
        self.stdscr.addstr(h-1, 0, help_text.ljust(w)[:w-1])
        self.stdscr.attroff(curses.A_REVERSE)
        
        self.stdscr.refresh()

# ==========================================
# ENTRÉE PRINCIPALE
# ==========================================
def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Serveur ProBook : python3 biclip.py --server")
        print("  Client TUI Arch : python3 biclip.py <IP_PROBOOK>")
        sys.exit(1)

    if sys.argv[1] == "--server":
        print(f"[*] Serveur Biclip centralisé démarré sur le port {PORT}...")
        try:
            start_central_server()
        except KeyboardInterrupt:
            print("\nArrêt du serveur.")
        sys.exit(0)

    # Client Mode Plein Écran
    server_ip = sys.argv[1]
    # Curses initialise le terminal et se ferme proprement même en cas de crash
    curses.wrapper(lambda stdscr: TUIClient(stdscr, server_ip).start())

if __name__ == "__main__":
    main()
