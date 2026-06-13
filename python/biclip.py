import socket
import threading
import sys

# --- CONFIGURATION ---
PORT = 9999  # Le port utilisé pour la communication
# ---------------------

# Variable en RAM qui stocke le presse-papier actuel
shared_clipboard = "[Presse-papier vide]"

def start_server():
    """Démarre un serveur en arrière-plan pour recevoir les 'push' de l'autre PC."""
    global shared_clipboard
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permet de réutiliser le port immédiatement après l'arrêt du script
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind(('0.0.0.0', PORT))
        server.listen(1)
    except Exception as e:
        print(\n[Erreur Serveur] Impossible de démarrer le serveur : {e})
        sys.exit(1)

    while True:
        try:
            conn, _ = server.accept()
            # Reçoit les données (limité à ~1 Mo pour cet outil de secours)
            data = conn.recv(1024 * 1024).decode('utf-8')
            if data:
                shared_clipboard = data
            conn.close()
        except:
            break

def send_push(target_ip, text):
    """Envoie (push) le texte vers l'autre ordinateur."""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Timeout de 3 secondes pour éviter que le terminal ne freeze si le PC est déconnecté
        client.settimeout(3.0)
        client.connect((target_ip, PORT))
        client.sendall(text.encode('utf-8'))
        client.close()
        print("[OK] Texte envoyé.")
    except Exception as e:
        print(f"[Erreur Push] Impossible de joindre {target_ip}:{PORT} ({e})")

def main():
    global shared_clipboard
    
    if len(sys.argv) < 2:
        print("Usage: python3 clipboard_emergency.py <IP_DE_L_AUTRE_PC>")
        sys.exit(1)
        
    target_ip = sys.argv[1]

    # Lancement du serveur dans un thread séparé pour écouter en arrière-plan
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()

    print(f"--- Outil de secours Presse-papier démarré ---")
    print(f"Écoute locale sur le port {PORT}")
    print(f"Cible configurée : {target_ip}")
    print("Commandes disponibles : 'push <texte>', 'pull', 'exit'\n")

    # Boucle principale (Interface TTY)
    while True:
        try:
            user_input = input("> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nFermeture...")
            break

        if not user_input:
            continue

        if user_input.lower() == 'exit':
            break
        elif user_input == 'pull':
            print(shared_clipboard)
        elif user_input.startswith('push '):
            # On extrait le texte après le mot "push "
            text_to_send = user_input[5:].strip()
            # Retire les guillemets si l'utilisateur en a mis autour de son texte
            if text_to_send.startswith('"') and text_to_send.endswith('"'):
                text_to_send = text_to_send[1:-1]
            elif text_to_send.startswith("'") and text_to_send.endswith("'"):
                text_to_send = text_to_send[1:-1]
                
            # Met à jour son propre presse-papier et l'envoie à l'autre
            shared_clipboard = text_to_send
            send_push(target_ip, text_to_send)
        else:
            print("Commande inconnue. Utilisez 'push <texte>', 'pull' ou 'exit'.")

if __name__ == '__main__':
    main()
