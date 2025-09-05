from libs.mqtt_controller import ESP_Controller
import sys
import time

magnet_control = ESP_Controller()
try:
    if len(sys.argv) == 2:
        if int(sys.argv[1]) == 1:
            magnet_control.magnet_control(True, False)
        if int(sys.argv[1]) == 2:
            magnet_control.magnet_control(False, True)

        print("Acik olan miknatis: ", int(sys.argv[1]))
        time.sleep(10)

    else:
        magnet_control.magnet_control(True, True)
        print("İki miknatis da acik")
        time.sleep(5)
        magnet_control.magnet_control(False, True)
        print("Miknatis 1 kapatildi")
        time.sleep(5)
        magnet_control.magnet_control(True, False)
        print("Miknatis 2 kapatildi")
        time.sleep(5)

except Exception as e:
    print(e)
finally:
    magnet_control.cleanup()