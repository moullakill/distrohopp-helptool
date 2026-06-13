#!/usr/bin/env python3
import sys
import socket
import threading
import time

PORT = 9999
BUFFER_SIZE = 4096
clipboard_content = "Vide"

def start_central_server():
    """Gère le stockage en RAM unique (À lancer sur le ProBook uniquement)."""
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
    """Envoie une commande au serveur central."""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.settimeout(3.0)
        client.connect((server_ip, PORT))
        client.sendall(message.encode('utf-8'))
        client.shutdown(socket.SHUT_WR)
        res = client.recv(BUFFER_SIZE).decode('utf-8')
        client.close()
        return res
    except Exception as e:
        return f"[Erreur] Connexion impossible avec le serveur {server_ip}: {e}"

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Sur le ProBook (Serveur) : python3 biclip.py --server")
        print("  Sur Arch (Client TTY)    : python3 biclip.py <IP_PROBOOK> push \"texte\"")
        print("  Sur Arch (Client TTY)    : python3 biclip.py <IP_PROBOOK> pull")
        sys.exit(1)

    # MODE SERVEUR (À lancer sur le ProBook)
    if sys.argv[1] == "--server":
        print(f"[*] Serveur Biclip centralisé démarré sur le port {PORT}...")
        print("[*] Laisse cette fenêtre ouverte. Tout est stocké en RAM ici.")
        try:
            start_central_server()
        except KeyboardInterrupt:
            print("\nArrêt du serveur.")
        sys.exit(0)

    # MODE CLIENT (Pour Arch ou le ProBook dans un autre TTY)
    server_ip = sys.argv[1]
    
    if len(sys.argv) > 2:
        action = sys.argv[2].lower()
        if action == "push" and len(sys.argv) > 3:
            res = send_to_server(server_ip, f"PUSH:{sys.argv[3]}")
            if res != "OK": print(res)
        elif action == "pull":
            print(send_to_server(server_ip, "PULL"))
        sys.exit(0)

    # Mode interactif client
    while True:
        try:
            user_input = input("biclip> ").strip()
            if not user_input or user_input.lower() == "exit": break
            if user_input.lower().startswith("push "):
                text = user_input[5:].strip('"\'')
                send_to_server(server_ip, f"PUSH:{text}")
            elif user_input.lower() == "pull":
                print(send_to_server(server_ip, "PULL"))
        except (KeyboardInterrupt, EOFError):
            break

if __name__ == "__main__":
    main()
