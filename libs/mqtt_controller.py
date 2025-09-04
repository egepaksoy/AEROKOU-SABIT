import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt

class Mqtt_Control():
    def __init__(self, ip="192.168.0.120", port=1883, topic="kontrol"):
        self.BROKER_ADRESS = ip
        self.BROKER_PORT = port
        self.TOPIC = topic

        self.client = mqtt.Client()
        self.client.connect(self.BROKER_ADRESS, self.BROKER_PORT, 60)

    def send_command(self, command):
        self.client.publish(self.TOPIC, command)
        print(f"[MQTT] Komut gönderildi: {command}")

    def magnet_control(self, magnet1: bool, magnet2: bool):
        if magnet1:
            self.send_command("em1_on")
        else:
            self.send_command("em1_off")

        if magnet2:
            self.send_command("em2_on")
        else:
            self.send_command("em2_off")

    def cleanup(self):
        self.send_command("em1_off")
        self.send_command("em2_off")

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