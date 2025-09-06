import socket

def receive_file(save_dir="C:/Users/Public/Videos/"):
    host = "0.0.0.0"  # Herkesten dinle
    port = 5001

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Sunucu başlatıldı. {port} portu dinleniyor...")

    while True:
        conn, addr = server_socket.accept()
        print(f"{addr} bağlandı.")

        # İlk gelen satır dosya adıdır
        filename = conn.recv(1024).decode().strip()
        filepath = save_dir + filename

        with open(filepath, "wb") as f:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                f.write(data)

        print(f"Dosya kaydedildi: {filepath}")
        conn.close()

if __name__ == "__main__":
    receive_file()
