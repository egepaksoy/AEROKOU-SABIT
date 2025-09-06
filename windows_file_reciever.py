import socket
import os

def receive_files(save_dir="C:/Users/Public/Videos/ucuslar/"):
    host = "0.0.0.0"  # Tüm ağ arayüzlerinden dinle
    port = 5001

    # Klasör yoksa oluştur
    os.makedirs(save_dir, exist_ok=True)

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Sunucu başlatıldı. {port} portu dinleniyor...")

    while True:
        conn, addr = server_socket.accept()
        print(f"{addr} bağlandı.")

        # Dosya adını al
        filename = conn.recv(1024).decode().strip()
        filepath = os.path.join(save_dir, filename)

        # Dosya verisini kaydet
        with open(filepath, "wb") as f:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                f.write(data)

        print(f"Dosya kaydedildi: {filepath}")
        conn.close()

if __name__ == "__main__":
    receive_files()
