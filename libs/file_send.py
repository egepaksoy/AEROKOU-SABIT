import socket
import os

def send_file(filepath, server_ip, server_port=5001):
    filesize = os.path.getsize(filepath)
    filename = os.path.basename(filepath)

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((server_ip, server_port))
        print(f"{filename} gönderiliyor ({filesize} bayt)...")

        # İlk olarak dosya adını gönder
        s.sendall(filename.encode() + b"\n")

        # Sonra dosya içeriğini gönder
        with open(filepath, "rb") as f:
            while True:
                bytes_read = f.read(4096)
                if not bytes_read:
                    break
                s.sendall(bytes_read)

        print("Gönderim tamamlandı.")
