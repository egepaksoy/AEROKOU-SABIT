import cv2
import math
import time
import json
import threading
from flask import Flask
#from picamera2 import Picamera2

from pymavlink_custom.pymavlink_custom import Vehicle
from libs.mqtt_controller import magnet_control, rotate_servo, cleanup
from libs.image_handler import image_recog_flask

#TODO: ucus oncesi parametrelerden WPNAV_SPEED parametresini 2 yapmak lazim (yavaslatsin diye)
def failsafe(vehicle, home_pos=None):
    def failsafe_drone_id(vehicle, drone_id, home_pos=None):
        if home_pos == None:
            print(f"{drone_id}>> Failsafe alıyor")
            vehicle.set_mode(mode="RTL", drone_id=drone_id)

        # guıdedli rtl
        else:
            print(f"{drone_id}>> Failsafe alıyor")
            vehicle.set_mode(mode="GUIDED", drone_id=drone_id)

            alt = vehicle.get_pos(drone_id=drone_id)[2]
            vehicle.go_to(loc=home_pos, alt=alt, drone_id=DRONE_ID)

            start_time = time.time()
            while True:
                if time.time() - start_time > 3:
                    print(f"{drone_id}>> RTL Alıyor...")
                    start_time = time.time()

                if vehicle.on_location(loc=home_pos, seq=0, sapma=1, drone_id=DRONE_ID):
                    print(f"{DRONE_ID}>> iniş gerçekleşiyor")
                    vehicle.set_mode(mode="LAND", drone_id=DRONE_ID)
                    break

    thraeds = []
    for d_id in vehicle.drone_ids:
        args = (vehicle, d_id)
        if home_pos != None:
            args = (vehicle, d_id, home_pos)

        thrd = threading.Thread(target=failsafe_drone_id, args=args)
        thrd.start()
        thraeds.append(thrd)


    for t in thraeds:
        t.join()

    print(f"{vehicle.drone_ids} id'li Drone(lar) Failsafe aldi")
    
def camera_distance(pos: list, screen_res: list, oran: float=0.3):
    orta_x1 = (screen_res[0] - (screen_res[0] * oran)) / 2
    orta_x2 = screen_res[0] - orta_x1
    orta_y1 = (screen_res[1] - (screen_res[1] * oran)) / 2
    orta_y2 = screen_res[1] - orta_y1

    pos_x, pos_y = pos

    x_dist = 0
    y_dist = 0
    
    if pos_x < orta_x1:
        x_dist = pos_x - orta_x1
    elif pos_x > orta_x2:
        x_dist = orta_x2 - pos_x
    if pos_y < orta_y1:
        y_dist = orta_y1 - pos_y
    elif pos_y > orta_y2:
        y_dist = orta_y2 - pos_y
    
    return x_dist, y_dist

def center_distance(pos: list, screen_res: list):
    return pos[0] - screen_res[0] / 2, screen_res[1] / 2 - pos[1]

def angle_from_center(pos, screen_res):
    cx, cy = screen_res[0] / 2.0, screen_res[1] / 2.0
    dx = pos[0] - cx
    dy = pos[1] - cy   # ekran koordinatında aşağı pozitif

    if dx == 0 and dy == 0:
        return 0.0  # merkezdeyse 0 derece diyelim

    # Normal atan2 kullanımı
    raw_angle = math.degrees(math.atan2(dy, dx))  # -180..180 (0° sağ)
    
    # Dönüştür: 0° yukarı olacak şekilde kaydır
    angle = (raw_angle + 90) % 360
    return angle

def is_near(old_pos, pos, pixel = 10):
    old_x, old_y = old_pos
    x, y = pos

    if abs(old_x - x) < pixel and abs(old_y - y) < pixel:
        return True
    return False

def ortala(obj_origin, DRONE_ID, shared_state, shared_state_lock, orta_oran, carpan: float=0.5):
    print(f"{DRONE_ID}>> BREAK Yapiyor")
    
    vehicle.move_drone_body((0,0,0), drone_id=DRONE_ID)

    while vehicle.get_speed(drone_id=DRONE_ID) > 0.1 and not stop_event.is_set():
        time.sleep(0.05)
    
    vehicle.set_mode(mode="GUIDED", drone_id=DRONE_ID)

    if carpan < 0.2:
        return False

    first_pos = vehicle.get_pos(drone_id=DRONE_ID)
    first_alt = first_pos[2]
    total_alt = first_alt

    if True:
        yukselme = 2
        total_alt = first_alt

        while not stop_event.is_set():
            with shared_state_lock:
                obj = shared_state["last_object"]
                obj_pos = shared_state["object_pos"]
                screen_res = shared_state["screen_res"]
    
            if obj != None:
                old_pos = obj_pos
                start_time = time.time()
                while time.time() - start_time <= 0.2:
                    with shared_state_lock:
                        obj = shared_state["last_object"]
                        obj_pos = shared_state["object_pos"]
                        screen_res = shared_state["screen_res"]
                    
                    if obj != None:
                        if is_near(old_pos=old_pos, pos=obj_pos):
                            break
                    
                    time.sleep(0.01)
                
                if obj != None:
                    if not is_near(old_pos=old_pos, pos=obj_pos):
                        obj = None
                
            if obj != None:
                if obj == obj_origin:
                    print(f"{DRONE_ID}>> {obj} bulundu")
                    break

            total_alt += yukselme

            if total_alt >= 10:
                print(f"{DRONE_ID}>> Cok yukseldi alcalip taramaya devam ediyor")
                vehicle.go_to(loc=first_pos, alt=first_alt, drone_id=DRONE_ID)
                while abs(vehicle.get_pos(drone_id=DRONE_ID)[2] - first_alt) > 0.1 and not stop_event.is_set():
                    time.sleep(0.2)
                return False

            vehicle.go_to(loc=first_pos, alt=total_alt, drone_id=DRONE_ID)
            
            print(f"{DRONE_ID}>> Daha genis arama icin {total_alt} metreye yukseliyor...")
            while abs(vehicle.get_pos(drone_id=DRONE_ID)[2] - total_alt) > 0.1 and not stop_event.is_set():
                time.sleep(0.2)
            
            print(f"{DRONE_ID}>> {total_alt} metreye yukseldi")

    with shared_state_lock:
        obj = shared_state["last_object"]
        obj_pos = shared_state["object_pos"]
        screen_res = shared_state["screen_res"]

    if obj != None:
        old_pos = obj_pos
        start_time = time.time()
        while time.time() - start_time <= 0.2:
            with shared_state_lock:
                obj = shared_state["last_object"]
                obj_pos = shared_state["object_pos"]
                screen_res = shared_state["screen_res"]
            
            if obj != None:
                if is_near(old_pos=old_pos, pos=obj_pos):
                    break
            
            time.sleep(0.01)
        
        if obj != None:
            if not is_near(old_pos=old_pos, pos=obj_pos):
                obj = None

    if obj == None:
        print("Nesne kayboldu")
        return False

    print(f"{DRONE_ID}>> {obj} ortalaniyor")
    
    x_centered = False
    y_centered = False
    
    while not stop_event.is_set() and x_centered == False:
        print(f"{DRONE_ID}>> Hedefe donuyor...")

        turn_angle = angle_from_center(obj_pos, screen_res)
        print(turn_angle)

        if turn_angle > 180:
            turn_angle -= 360

        turn_angle *= -1
        print("Donus acisi: ", turn_angle)

        vehicle.turn_way(turn_angle=turn_angle, drone_id=DRONE_ID)

        while vehicle.yaw_speed(drone_id=DRONE_ID) < 0.02:
            time.sleep(0.05)

        while vehicle.yaw_speed(drone_id=DRONE_ID) >= 0.02:
            time.sleep(0.05)
        
        print(f"{DRONE_ID}>> Hedefe donuldu")
        #TODO: bunu kaldir
        x_centered = True
        break

        with shared_state_lock:
            obj = shared_state["last_object"]
            obj_pos = shared_state["object_pos"]
            screen_res = shared_state["screen_res"]

        if obj != None:
            old_pos = obj_pos
            start_time = time.time()
            while time.time() - start_time <= 0.2:
                with shared_state_lock:
                    obj = shared_state["last_object"]
                    obj_pos = shared_state["object_pos"]
                    screen_res = shared_state["screen_res"]
                
                if obj != None:
                    if is_near(old_pos=old_pos, pos=obj_pos):
                        break
                
                time.sleep(0.01)
            
            if obj != None:
                if not is_near(old_pos=old_pos, pos=obj_pos):
                    obj = None
        
        if obj == None:
            print("Nesne kayboldu")
            return False
        
        if camera_distance(obj_pos, screen_res, orta_oran)[0] == 0:
            x_centered = True

    #? Dronu nesneye ilerletme
    start_time_drone = time.time()
    start_time = time.time()
    while not stop_event.is_set() and not y_centered and time.time() - start_time_drone < 15:
        if time.time() - start_time >= 3:
            print(f"{DRONE_ID}>> Hedefe ilerliyor")
            start_time = time.time()
        vehicle.move_drone_body(rota=(carpan, 0, 0), drone_id=DRONE_ID)

        with shared_state_lock:
            obj = shared_state["last_object"]
            obj_pos = shared_state["object_pos"]
            screen_res = shared_state["screen_res"]
        
        if obj != None:
            if camera_distance(obj_pos, screen_res, orta_oran)[1] == 0:
                print(f"{DRONE_ID}>> Drone Y'De ortalandi")
                y_centered = True
                
                vehicle.move_drone_body((0,0,0), drone_id=DRONE_ID)

                start_time = time.time()
                while time.time() - start_time < 1 and not stop_event.is_set():
                    time.sleep(0.05)
                
                vehicle.set_mode(mode="GUIDED", drone_id=DRONE_ID)

                break
        
        time.sleep(0.05)

    if x_centered and y_centered:
        return True
    
    return False

def drop_obj(miknatis):
    start_time = time.time()
    while time.time() - start_time < 2 and not stop_event.is_set():
        time.sleep(0.05)

    #! Test
    if miknatis == 2:
        magnet_control(True, False)
    else:
        magnet_control(False, True)
    print(f"mıknatıs {miknatis} kapatıldı")

    start_time = time.time()
    while time.time() - start_time < 3 and not stop_event.is_set():
        time.sleep(0.05)

    return True

def go_home(stop_event, vehicle: Vehicle, home_pos, DRONE_ID):
    vehicle.go_to(loc=home_pos, drone_id=DRONE_ID)
    print(f"{DRONE_ID}>> kalkış konumuna dönüyor...")

    start_time = time.time()
    while not stop_event.is_set():
        if time.time() - start_time > 5:
            print(f"{DRONE_ID}>> kalkış konumuna dönüyor...")
            start_time = time.time()
        
        if vehicle.on_location(loc=home_pos, seq=0, sapma=1, drone_id=DRONE_ID):
            print(f"{DRONE_ID}>> iniş gerçekleşiyor")
            vehicle.set_mode(mode="LAND", drone_id=DRONE_ID)
            break

stop_event = threading.Event()
config = json.load(open("./config.json", "r"))

# Algilananlari kullanma
shared_state = {"last_object": None, "object_pos": None, "screen_res": None}
shared_state_lock = threading.Lock()
objects = config["OBJECTS"]

dropped_objects = []
sonra_birakilcak_obj = None
sonra_birakilcak_pos = None

'''
picam2 = Picamera2()
picam2.configure(picam2.create_video_configuration(main={"format": "RGB888", "size": (640, 480)}))
picam2.start()
time.sleep(2)  # Kamera başlatma süresi için bekle
'''
cap = cv2.VideoCapture(0)

orta_oran = config["ORTA"]

# Görüntü işleme
app = Flask(__name__)
broadcast_started = threading.Event()
port = config["UDP-PORT"]
# Raspberry ile
threading.Thread(target=image_recog_flask, args=(cap, port, broadcast_started, stop_event, shared_state, shared_state_lock, orta_oran), daemon=True).start()

# Erkenden miknatisi calistirma
input("Mıknatıslar bağlandığında ENTER tuşuna basın")

# Drone ayarlamalari
vehicle = Vehicle(config["CONN-STR"])
DRONE_ID = config["DRONE"]["id"]
ALT = config["DRONE"]["alt"]

# Tarama ayarlama
drone_locs = vehicle.get_wp_list(drone_id=DRONE_ID)
if len(drone_locs) == 0:
    raise ValueError("Waypointler okunamadi")
ALT = drone_locs[0][2]

print(f"tarama wp sayısı: {len(drone_locs)}")

try:
    # Görüntü gelmesini bekle
    while not stop_event.is_set() and not broadcast_started.is_set():
        time.sleep(0.5)
    
    #!rotate_servo(0)
    print("servo duruyor")

    # Takeoff
    vehicle.set_mode("GUIDED", drone_id=DRONE_ID)
    vehicle.arm_disarm(True, drone_id=DRONE_ID)
    vehicle.takeoff(ALT, drone_id=DRONE_ID)

    home_pos = vehicle.get_pos(drone_id=DRONE_ID)
    print(f"{DRONE_ID}>> Kalkış tamamlandı")

    # Tarama başlangıcı
    current_loc = 0
    vehicle.go_to(loc=drone_locs[current_loc], alt=ALT, drone_id=DRONE_ID)

    print(f"{DRONE_ID}>> Alan taraniyor")
    while not stop_event.is_set() and len(dropped_objects) != 2:
        with shared_state_lock:
            obj = shared_state["last_object"]
 
        if obj != None:
            counter = 0
            start_time = time.time()
            while time.time() - start_time <= 0.1 and counter < (0.1 / 0.01) / 3:
                with shared_state_lock:
                    obj = shared_state["last_object"]
                
                if obj != None:
                    counter += 1
                
                time.sleep(0.01)
            
            if counter < (0.1 / 0.01) / 3:
                obj = None
        
        if obj != None:
            if obj not in dropped_objects:
                # İlk hedefe yuk birakma kodu
                if (objects[obj]["sira"] == 1 or len(dropped_objects) == 1):
                    print(obj)
                    miknatis = objects[obj]["miknatis"]
                    
                    ortalandi = ortala(obj, DRONE_ID, shared_state, shared_state_lock, orta_oran)

                    if ortalandi == False:
                        print(f"{DRONE_ID}>> {obj} ortalanamadi")
                    else:
                        print(f"{DRONE_ID}>> {obj} ortalandi yuk birakiliyor")
                        #drop_obj(miknatis)
                        print(f"{DRONE_ID}>> Drone {obj} yükünü bıraktı")
                    
                        dropped_objects.append(obj)
                    vehicle.go_to(loc=drone_locs[current_loc], alt=ALT, drone_id=DRONE_ID)
                
                # ikinci hedefi ekleme kodu
                elif sonra_birakilcak_obj == None:
                    print(f"{obj} Algilandi duruyor")

                    vehicle.move_drone_body((0,0,0), drone_id=DRONE_ID)
                    start_time = time.time()
                    while not time.time() - start_time <= 1.5:
                        time.sleep(0.05)

                    sonra_birakilcak_obj = obj
                    sonra_birakilcak_pos = vehicle.get_pos(drone_id=DRONE_ID)

                    print(f"{obj} Sonra birakilmak icin verileri alindi tarama devam ediyor")
                
                    vehicle.go_to(loc=drone_locs[current_loc], alt=ALT, drone_id=DRONE_ID)
        
        # İlk hedefe yuk birakildi ise ikinci hedefe yuk birakma kodu
        if sonra_birakilcak_obj != None and len(dropped_objects) == 1 and sonra_birakilcak_pos != None:
            vehicle.go_to(loc=sonra_birakilcak_pos, alt=ALT, drone_id=DRONE_ID)

            while not vehicle.on_location(loc=sonra_birakilcak_pos, drone_id=DRONE_ID):
                time.sleep(0.2)
                    
            print(sonra_birakilcak_obj)
            miknatis = objects[sonra_birakilcak_obj]["miknatis"]
            
            ortalandi = ortala(sonra_birakilcak_obj, DRONE_ID, shared_state, shared_state_lock, orta_oran)

            if ortalandi == False:
                print(f"{DRONE_ID}>> {sonra_birakilcak_obj} ortalanamadi")
            else:
                print(f"{DRONE_ID}>> {sonra_birakilcak_obj} ortalandi yuk birakiliyor")
                #!drop_obj(miknatis)
                print(f"{DRONE_ID}>> Drone {sonra_birakilcak_obj} yükünü bıraktı")
            
                dropped_objects.append(sonra_birakilcak_obj)

            sonra_birakilcak_obj = None
            sonra_birakilcak_pos = None
        
        # Hedeflere yuk birakildi ise bitirme kodu
        if len(dropped_objects) == 2:
            print(f"{DRONE_ID}>> İki hedefe de yuk birakildi gorev bitiriliyor")
            break

        # Sonraki wayponite gelme kodu
        if vehicle.on_location(loc=drone_locs[current_loc], seq=0, sapma=1, drone_id=DRONE_ID):
            #!rotate_servo(0)

            print(f"{DRONE_ID}>> wp: {current_loc + 1}/{len(drone_locs)} ulasildi")

            # Hedeflere birakildi ise taramayi bitirme kodu
            if len(dropped_objects) == 2:
                print(f"{DRONE_ID}>> İki hedefe de yuk birakildi gorev bitiriliyor")
                break

            # Tarama bittiyse
            if current_loc + 1 == len(drone_locs):
                # İkinci hedef varsa yuk birakma kodu
                if sonra_birakilcak_obj != None and sonra_birakilcak_pos != None and len(dropped_objects) != 2:
                    vehicle.go_to(loc=sonra_birakilcak_pos, alt=ALT, drone_id=DRONE_ID)

                    while not vehicle.on_location(loc=sonra_birakilcak_pos, drone_id=DRONE_ID):
                        time.sleep(0.2)
                            
                    print(sonra_birakilcak_obj)
                    miknatis = objects[sonra_birakilcak_obj]["miknatis"]
                    
                    ortalandi = ortala(sonra_birakilcak_obj, DRONE_ID, shared_state, shared_state_lock, orta_oran)

                    if ortalandi == False:
                        print(f"{DRONE_ID}>> {sonra_birakilcak_obj} ortalanamadi")
                    else:
                        print(f"{DRONE_ID}>> {sonra_birakilcak_obj} ortalandi yuk birakiliyor")
                        #drop_obj(miknatis)
                        print(f"{DRONE_ID}>> Drone {sonra_birakilcak_obj} yükünü bıraktı")
                    
                        dropped_objects.append(sonra_birakilcak_obj)

                    sonra_birakilcak_obj = None
                    sonra_birakilcak_pos = None

                print(f"{DRONE_ID}>> Drone taramayı bitirdi")
                break
            
            # Tarama bitmediyse sonraki wp'ye gec
            else:
                current_loc += 1
                vehicle.go_to(loc=drone_locs[current_loc], alt=ALT, drone_id=DRONE_ID)
                print(f"{DRONE_ID}>> {current_loc + 1}/{len(drone_locs)}. konuma gidiyor...")

        time.sleep(0.02)

    print(dropped_objects)

    go_home(stop_event, vehicle, home_pos, DRONE_ID)

    print("Görev tamamlandı")

except KeyboardInterrupt:
    print("Klavye ile çıkış yapıldı")
    if "home_pos" in locals():
        failsafe(vehicle, home_pos)
    else:
        failsafe(vehicle)

except Exception as e:
    if "home_pos" in locals():
        failsafe(vehicle, home_pos)
    else:
        failsafe(vehicle)
    print("Hata:", e)

finally:
    vehicle.vehicle.close()
    input("Servoyu kapatmak için Enter'a basın")
    #!cleanup()
    print("GPIO temizlendi, bağlantı kapatıldı")