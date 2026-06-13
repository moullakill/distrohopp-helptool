#!/usr/bin/env python3
import sys
import socket
import threading
import time

# Configuration par défaut
PORT = 9999
BUFFER_SIZE = 4096

# Stockage en RAM
clipboard_content = ""

def start_server():
    """Micro-service d'arrière-plan qui écoute les connexions entrantes."""
    global clipboard_content
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Permet de réutiliser le port immédiatement après l'arrêt
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        server.bind(('0.0.0.0', PORT))
        server.listen(5)
    except Exception as e:
        print(f"\n[Erreur Serveur] Impossible de démarrer le serveur sur le port {PORT}: {e}")
        return

    while True:
        try:
            conn, addr = server.accept()
            data = conn.recv(BUFFER_SIZE).decode('utf-8')
            if data:
                if data.startswith("PUSH:"):
                    # On extrait le texte et on overwrite le précédent
                    clipboard_content = data[5:]
                    conn.sendall(b"OK")
                elif data == "PULL":
                    # On renvoie le contenu actuel en RAM
                    conn.sendall(clipboard_content.encode('utf-8'))
            conn.close()
        except Exception:
            pass

def send_request(ip, message):
    """Fonction utilitaire pour envoyer une commande à l'autre machine."""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Timeout court pour éviter de bloquer le terminal si l'autre est déco
        client.settimeout(3.0) 
        client.connect((ip, PORT))
        client.sendall(message.encode('utf-8'))
        response = client.recv(BUFFER_SIZE).decode('utf-8')
        client.close()
        return response
    except Exception as e:
        return f"[Erreur Connexion] Impossible de joindre {ip}:{PORT} ({e})"

def main():
    global clipboard_content
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Démarrer le mode interactif : python3 biclip.py <IP_AUTRE_MACHINE>")
        print("  Commande directe (TTY)     : python3 biclip.py <IP_AUTRE_MACHINE> push \"votre texte\"")
        print("  Commande directe (TTY)     : python3 biclip.py <IP_AUTRE_MACHINE> pull")
        sys.exit(1)

    target_ip = sys.argv[1]

    # Lancement du micro-service d'arrière-plan en tâche de fond (Thread)
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    
    # Petite pause pour laisser le serveur s'initialiser
    time.sleep(0.1)

    # Mode Commande Directe (TTY / One-liner)
    if len(sys.argv) > 2:
        action = sys.argv[2].lower()
        if action == "push" and len(sys.argv) > 3:
            text_to_send = sys.argv[3]
            # On met à jour notre RAM locale ET on push chez l'autre
            clipboard_content = text_to_send
            send_request(target_ip, f"PUSH:{text_to_send}")
        elif action == "pull":
            # On demande le texte de l'autre machine
            res = send_request(target_ip, "PULL")
            print(res)
        else:
            print("Commande TTY invalide.")
        sys.exit(0)

    # Mode Live User Texte (Interactif)
    print(f"--- Biclip activé ---")
    print(f"Connecté vers : {target_ip} | Port local d'écoute : {PORT}")
    print("Commandes disponibles : push \"votre texte\" / pull / exit")
    print("----------------------")

    while True:
        try:
            user_input = input("biclip> ").strip()
            if not user_input:
                continue
            
            if user_input.lower() == "exit":
                break
            
            elif user_input.lower().startswith("push "):
                # On récupère tout ce qui suit "push "
                text_to_send = user_input[5:].strip('"\'') 
                clipboard_content = text_to_send
                send_request(target_ip, f"PUSH:{text_to_send}")
                
            elif user_input.lower() == "pull":
                res = send_request(target_ip, "PULL")
                print(res)
                
            else:
                print("Commande inconnue. Utilisez 'push \"texte\"', 'pull' ou 'exit'.")
        except (KeyboardInterrupt, EOFError):
            print("\nFermeture de Biclip.")
            break

if __name__ == "__main__":
    main()
