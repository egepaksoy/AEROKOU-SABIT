import RPi.GPIO as GPIO
import time
import subprocess
import serial
import os

class ESP_Controller:
    def __init__(self, mac_address="00:4B:12:3E:B8:52", rfcomm_dev="/dev/rfcomm0", baudrate=9600):
        self.mac_address = mac_address
        self.rfcomm_dev = rfcomm_dev
        self.baudrate = baudrate
        self.process = None
        self.serial_conn = None

        self.connect()

    def connect(self):
        """
        ESP32 ile RFCOMM bağlantısı kurar.
        """
        # Önce eski bağlantıyı serbest bırak
        subprocess.run(["sudo", "rfcomm", "release", "hci0"], stderr=subprocess.DEVNULL)

        print(f"{self.mac_address} adresindeki ESP32'ye bağlanılıyor...")
        self.process = subprocess.Popen(
            ["sudo", "rfcomm", "connect", "hci0", self.mac_address, "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        time.sleep(5)  # bağlantı için bekle

        if os.path.exists(self.rfcomm_dev):
            print("RFCOMM seri port oluşturuldu:", self.rfcomm_dev)
            self.serial_conn = serial.Serial(self.rfcomm_dev, baudrate=self.baudrate, timeout=1)
            return True
        else:
            print("Hata: RFCOMM seri port oluşmadı!")
            return False

    def send_message(self, message):
        """
        ESP32'ye mesaj gönderir ve cevabı okur.
        """
        if not self.serial_conn:
            print("Hata: ESP32 ile seri bağlantı kurulmamış.")
            return None

        self.serial_conn.write((message + "\n").encode())
        print("Gönderildi:", message)

        response = self.serial_conn.readline().decode().strip()
        if response:
            print("ESP32'den cevap:", response)
        return response
    
    def magnet_control(self, magnet1: bool, magnet2: bool):
        if magnet1:
            self.send_message("em1_on")
        else:
            self.send_message("em1_off")

        if magnet2:
            self.send_message("em2_on")
        else:
            self.send_message("em2_off")

    def disconnect(self):
        """
        Bağlantıyı güvenli şekilde kapatır.
        """
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            print("Seri bağlantı kapatıldı.")

        subprocess.run(["sudo", "rfcomm", "release", "hci0"])
        print("RFCOMM bağlantısı kapatıldı.")

        if self.process:
            self.process.terminate()
    
    def cleanup(self):
        self.magnet_control(False, False)
        self.disconnect()

class Servo_Control():
    def __init__(self, servo_pin=17):
        self.servo_pin = servo_pin

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(servo_pin, GPIO.OUT)

        self.pwm = GPIO.PWM(servo_pin, 50)
        self.pwm.start(0)

    def rotate_servo(self, direction):
        if direction == 1:
            self.pwm.ChangeDutyCycle(8.0)

        elif direction == -1:
            self.pwm.ChangeDutyCycle(6.0)

        elif direction == 0:
            self.pwm.ChangeDutyCycle(7.5)

    def cleanup(self):
        GPIO.cleanup()
        self.pwm.stop()