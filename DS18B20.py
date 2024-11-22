#!/usr/bin/env python3
import os
import time
import RPi.GPIO as GPIO
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import paho.mqtt.client as mqtt  # For ThingsBoard integration
import config  # Assuming you have your configuration values in config.py

# GPIO setup for controlling the fan (GPIO6)
FAN_PIN = 23
GPIO.setmode(GPIO.BCM)
GPIO.setup(FAN_PIN, GPIO.OUT)

# MQTT Setup (AWS)
MQTT_CLIENT_ID = "RaspberryPiTemperatureFanControl"
MQTT_TOPIC = "champlain/sensor/69/data"

# ThingsBoard MQTT Setup
THINGSBOARD_HOST = "demo.thingsboard.io"  # ThingsBoard MQTT broker address
THINGSBOARD_ACCESS_TOKEN = "ZtW5UexhXNptd2EncmXB"  # Your ThingsBoard device access token

# Setup MQTT client for AWS
def setupAWSIoTMQTT():
    client = AWSIoTMQTTClient(MQTT_CLIENT_ID)
    client.configureEndpoint(config.AWS_HOST, config.AWS_PORT)
    client.configureCredentials(config.AWS_ROOT_CA, config.AWS_PRIVATE_KEY, config.AWS_CLIENT_CERT)
    client.configureOfflinePublishQueueing(config.OFFLINE_QUEUE_SIZE)  # Infinite offline publish queueing
    client.configureDrainingFrequency(config.DRAINING_FREQ)  # Draining frequency in Hz
    client.configureConnectDisconnectTimeout(config.CONN_DISCONN_TIMEOUT)  # 10 seconds
    client.configureMQTTOperationTimeout(config.MQTT_OPER_TIMEOUT)  # 5 seconds
    return client

# Setup MQTT client for ThingsBoard
def setupThingsBoardMQTT():
    client = mqtt.Client()
    client.username_pw_set(THINGSBOARD_ACCESS_TOKEN)  # Set ThingsBoard device token as the username
    client.connect(THINGSBOARD_HOST, 1883, 60)  # Connect to ThingsBoard
    return client

# Callback for RPC requests (from the first script)
def on_rpc_request(client, userdata, message):
    try:
        payload = json.loads(message.payload.decode("utf-8"))
        method = payload.get('method')
        params = payload.get('params')
        
        if method == 'setState':
            if params:
                if params:  # If 'true', turn on the fan; if 'false', turn off the fan
                    GPIO.output(FAN_PIN, GPIO.HIGH)  # Fan On
                    print("Fan ON")
                    state = "On"
                else:
                    GPIO.output(FAN_PIN, GPIO.LOW)  # Fan Off
                    print("Fan OFF")
                    state = "Off"

                # Send the state of the fan back to ThingsBoard
                tb_payload = {
                    "power": state,
                }
                client.publish("v1/devices/me/attributes", json.dumps(tb_payload), qos=1)
                print(f"Published to ThingsBoard: {tb_payload}")
    except Exception as e:
        print(f"Error handling RPC: {e}")

# Reads temperature from sensor and prints to stdout
# id is the id of the sensor
def readSensor(id, mqtt_client, tb_mqtt_client, threshold):
    try:
        with open(f"/sys/bus/w1/devices/{id}/w1_slave") as tfile:
            text = tfile.read()
        secondline = text.split("\n")[1]
        temperaturedata = secondline.split(" ")[9]
        temperature = float(temperaturedata[2:]) / 1000
        
        # Publish temperature data to AWS IoT MQTT
        payload = {
            "temperature": temperature,
        }
        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload), 1)
        print(f"Published to AWS: {payload}")

        # Publish temperature data to ThingsBoard
        tb_payload = {
            "temperature": temperature,
        }
        tb_mqtt_client.publish("v1/devices/me/telemetry", json.dumps(tb_payload), qos=1)
        print(f"Published to ThingsBoard: {tb_payload}")

        # Control fan based on temperature
        if temperature > threshold:
            GPIO.output(FAN_PIN, GPIO.HIGH)  # Turn fan ON
            print("Fan ON")
            # Send power state to ThingsBoard
            payload = json.dumps({"power": "On"})
            tb_mqtt_client.publish("v1/devices/me/attributes", payload, qos=1)
            print("Published power: On")
            
            time.sleep(5)  # Keep fan on for 5 seconds
            GPIO.output(FAN_PIN, GPIO.LOW)  # Turn fan OFF
            print("Fan OFF")
            # Send power state to ThingsBoard
            payload = json.dumps({"power": "Off"})
            tb_mqtt_client.publish("v1/devices/me/attributes", payload, qos=1)
            print("Published power: Off")
        else:
            GPIO.output(FAN_PIN, GPIO.LOW)  # Turn fan OFF
            print("Fan OFF")
            # Send power state to ThingsBoard
            payload = json.dumps({"power": "Off"})
            tb_mqtt_client.publish("v1/devices/me/attributes", payload, qos=1)
            print("Published power: Off")
    
    except FileNotFoundError:
        print(f"Sensor {id} not found. Check the connection.")

# Reads temperature from all sensors found in /sys/bus/w1/devices/
# starting with "28-..."
def readSensors(mqtt_client, tb_mqtt_client, threshold):
    count = 0
    for file in os.listdir("/sys/bus/w1/devices/"):
        if file.startswith("28-"):
            readSensor(file, mqtt_client, tb_mqtt_client, threshold)
            count += 1
    if count == 0:
        print("No sensor found! Check connection.")

# Read temperature every second for all connected sensors
def loop(mqtt_client, tb_mqtt_client, threshold):
    while True:
        readSensors(mqtt_client, tb_mqtt_client, threshold)
        time.sleep(1)

# Nothing to cleanup
def destroy():
    GPIO.cleanup()

# Main starts here
if __name__ == "__main__":
    try:
        # Ask user for the threshold or use the default
        default_threshold = 25.0
        print(f"The default threshold is set to: {default_threshold} Degrees.")
        user_input = input("Do you want to continue with default? (Y/N): ").strip().upper()
        
        if user_input == 'Y':
            threshold = default_threshold
        else:
            threshold = float(input("Please enter the threshold temperature (in degrees): ").strip())
        
        # Initialize AWS IoT MQTT client
        mqtt_client = setupAWSIoTMQTT()
        mqtt_client.connect()
        print("AWS IoT MQTT Client connected successfully.")
        
        # Initialize ThingsBoard MQTT client
        tb_mqtt_client = setupThingsBoardMQTT()
        tb_mqtt_client.on_message = on_rpc_request  # Set up the RPC request handler
        tb_mqtt_client.subscribe("v1/devices/me/rpc/request/+")
        tb_mqtt_client.loop_start()  # Start the loop to process MQTT messages
        print("ThingsBoard MQTT Client connected successfully.")
        
        loop(mqtt_client, tb_mqtt_client, threshold)
    except KeyboardInterrupt:
        destroy()
        print("Program terminated.")
