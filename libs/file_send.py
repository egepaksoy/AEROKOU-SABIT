import socket
import datetime
import os

def send_file(filepath, server_ip="192.168.0.119", server_port=5001):
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

def send_today_videos(folder="ucusalar", ip="192.168.0.119", port=5001):
    today_str = datetime.now().strftime("%Y-%m-%d")  # Örn: 2025-09-06
    print(f"Bugünkü videolar ({today_str}) aranıyor...")

    # "ucuslar" klasöründeki bütün dosyaları listele
    for filename in os.listdir(folder):
        if filename.startswith(f"ucus-{today_str}"):  # Bugünkü videolar
            filepath = os.path.join(folder, filename)
            send_file(filepath, ip, port)