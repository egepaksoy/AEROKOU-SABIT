import socket
import datetime
import os

FOLDER = "ucuslar"              # Videoların klasörü
SERVER_IP = "192.168.0.119"      # Windows cihazın IP adresi
SERVER_PORT = 5001              # Alıcı port (Windows tarafında açık olmalı)

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

        print(f"{filename} Gönderim tamamlandı.")

def send_today_videos():
    today_str = datetime.now().strftime("%Y-%m-%d")  # Örn: 2025-09-06
    print(f"Bugünkü videolar ({today_str}) aranıyor...")

    # "ucuslar" klasöründeki bütün dosyaları listele
    for filename in os.listdir(FOLDER):
        if filename.startswith(f"ucus-{today_str}"):  # Bugünkü videolar
            filepath = os.path.join(FOLDER, filename)
            send_file(filepath, SERVER_IP, SERVER_PORT)