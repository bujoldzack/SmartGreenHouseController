#!/usr/bin/env python
import ADC0832
import time
import RPi.GPIO as GPIO
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import config  # Assuming you have your configuration values in config.py

LED = 4
Lamp_Pin = 19  # Pin for controlling the lamp

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED, GPIO.OUT)
GPIO.setup(Lamp_Pin, GPIO.OUT)  # Set up the lamp pin

myPWM = GPIO.PWM(LED, 10)
myPWM.start(50)

# MQTT Setup
MQTT_CLIENT_ID = "RaspberryPiLightSensor"
MQTT_TOPIC = "champlain/sensor/69/data"

def setupMQTT():
    client = AWSIoTMQTTClient(MQTT_CLIENT_ID)
    client.configureEndpoint(config.AWS_HOST, config.AWS_PORT)
    client.configureCredentials(config.AWS_ROOT_CA, config.AWS_PRIVATE_KEY, config.AWS_CLIENT_CERT)
    client.configureOfflinePublishQueueing(config.OFFLINE_QUEUE_SIZE)  # Infinite offline publish queueing
    client.configureDrainingFrequency(config.DRAINING_FREQ)  # Draining frequency in Hz
    client.configureConnectDisconnectTimeout(config.CONN_DISCONN_TIMEOUT)  # 10 seconds
    client.configureMQTTOperationTimeout(config.MQTT_OPER_TIMEOUT)  # 5 seconds
    return client

def init():
    ADC0832.setup()
    # Setup MQTT connection
    mqtt_client = setupMQTT()
    mqtt_client.connect()
    print("MQTT Client connected successfully.")
    return mqtt_client

def loop(mqtt_client):
    while True:
        res = ADC0832.getADC(0)
        vol = 3.3 / 255 * res
        lux = res * 100 / 255
        myPWM.ChangeDutyCycle(lux)
        time.sleep(0.2)

        # Prepare payload for MQTT
        payload = {
            "lux": lux,
            "light_condition": "dark" if res < 128 else "light"
        }
        
        # Publish to MQTT topic
        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), 1)

        if res < 128:  # Threshold for dark condition (low light)
            print("dark")
            GPIO.output(LED, GPIO.HIGH)  # Turn off LED
            GPIO.output(Lamp_Pin, GPIO.HIGH)  # Turn off the lamp
        else:
            print("light")
            GPIO.output(LED, GPIO.LOW)  # Turn on LED
            GPIO.output(Lamp_Pin, GPIO.LOW)  # Turn on the lamp

        time.sleep(0.2)

if __name__ == '__main__':
    mqtt_client = init()
    try:
        loop(mqtt_client)
    except KeyboardInterrupt:
        ADC0832.destroy()
        print('The end!')
