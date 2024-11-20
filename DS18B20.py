#!/usr/bin/env python3
import os
import time
import RPi.GPIO as GPIO
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import config  # Assuming you have your configuration values in config.py

# GPIO setup for controlling the fan (GPIO6)
FAN_PIN = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(FAN_PIN, GPIO.OUT)

# MQTT Setup
MQTT_CLIENT_ID = "RaspberryPiTemperatureFanControl"
MQTT_TOPIC = "champlain/sensor/69/data"

# Setup MQTT client
def setupMQTT():
    client = AWSIoTMQTTClient(MQTT_CLIENT_ID)
    client.configureEndpoint(config.AWS_HOST, config.AWS_PORT)
    client.configureCredentials(config.AWS_ROOT_CA, config.AWS_PRIVATE_KEY, config.AWS_CLIENT_CERT)
    client.configureOfflinePublishQueueing(config.OFFLINE_QUEUE_SIZE)  # Infinite offline publish queueing
    client.configureDrainingFrequency(config.DRAINING_FREQ)  # Draining frequency in Hz
    client.configureConnectDisconnectTimeout(config.CONN_DISCONN_TIMEOUT)  # 10 seconds
    client.configureMQTTOperationTimeout(config.MQTT_OPER_TIMEOUT)  # 5 seconds
    return client

# Reads temperature from sensor and prints to stdout
# id is the id of the sensor
def readSensor(id, mqtt_client):
    try:
        with open(f"/sys/bus/w1/devices/{id}/w1_slave") as tfile:
            text = tfile.read()
        secondline = text.split("\n")[1]
        temperaturedata = secondline.split(" ")[9]
        temperature = float(temperaturedata[2:]) / 1000
        
        # Publish temperature data to MQTT
        payload = {
            "temperature": temperature,
        }
        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), 1)
        print(f"Published: {payload}")

        # Control fan based on temperature
        if temperature > 25.0:
            GPIO.output(FAN_PIN, GPIO.HIGH)  # Turn fan ON
            print("Fan ON")
            time.sleep(5)  # Keep fan on for 5 seconds
            GPIO.output(FAN_PIN, GPIO.LOW)  # Turn fan OFF
            print("Fan OFF")
        else:
            GPIO.output(FAN_PIN, GPIO.LOW)  # Turn fan OFF
            print("Fan OFF")
    
    except FileNotFoundError:
        print(f"Sensor {id} not found. Check the connection.")

# Reads temperature from all sensors found in /sys/bus/w1/devices/
# starting with "28-..."
def readSensors(mqtt_client):
    count = 0
    for file in os.listdir("/sys/bus/w1/devices/"):
        if file.startswith("28-"):
            readSensor(file, mqtt_client)
            count += 1
    if count == 0:
        print("No sensor found! Check connection.")

# Read temperature every second for all connected sensors
def loop(mqtt_client):
    while True:
        readSensors(mqtt_client)
        time.sleep(1)

# Nothing to cleanup
def destroy():
    GPIO.cleanup()

# Main starts here
if __name__ == "__main__":
    try:
        mqtt_client = setupMQTT()
        mqtt_client.connect()
        print("MQTT Client connected successfully.")
        loop(mqtt_client)
    except KeyboardInterrupt:
        destroy()
        print("Program terminated.")
