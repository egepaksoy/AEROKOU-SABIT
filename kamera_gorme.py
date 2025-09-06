import cv2
import time
import json
import threading
from flask import Flask
import sys

from libs.mqtt_controller import ESP_Controller
from libs.image_handler import image_recog_flask

stop_event = threading.Event()
config = json.load(open("./config.json", "r"))

# Algilananlari kullanma
shared_state = {"last_object": None, "object_pos": None, "screen_res": None}
shared_state_lock = threading.Lock()
objects = config["OBJECTS"]

dropped_objects = []
sonra_birakilcak_obj = None
sonra_birakilcak_pos = None

if len(sys.argv) == 2:
    if sys.argv[1] == "test":
        cap = cv2.VideoCapture(0)
    
    else:
        raise ValueError("Test etmek icin kodu test ile baslatin: python gorev2.py test")

if "cap" not in locals():
    from picamera2 import Picamera2

    cap = Picamera2()
    cap.configure(cap.create_video_configuration(main={"format": "RGB888", "size": (640, 480)}))
    cap.start()
    time.sleep(2)  # Kamera başlatma süresi için bekle

orta_oran = config["ORTA"]

magnet_control = ESP_Controller()

# Görüntü işleme
app = Flask(__name__)
broadcast_started = threading.Event()
port = config["UDP-PORT"]
# Raspberry ile
threading.Thread(target=image_recog_flask, args=(cap, port, broadcast_started, stop_event, shared_state, shared_state_lock, orta_oran), daemon=True).start()

# Erkenden miknatisi calistirma
try:
    magnet_control.magnet_control(True, True)
    input("Mıknatıslar bağlandığında ENTER tuşuna basın")
finally:
    magnet_control.cleanup()