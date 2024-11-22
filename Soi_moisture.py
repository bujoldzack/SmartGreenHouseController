#!/usr/bin/env python3
import RPi.GPIO as GPIO
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import paho.mqtt.client as mqtt
import time
import json
import config

# RGB light pins
colors = [0x00FF00, 0x0000FF]  # Green, Blue colors

R = 36
G = 38
B = 40

# Pin configuration for SPI interface
PIN_CLK = 12
PIN_DO = 13
PIN_DI = 15
PIN_CS = 11

# AWS IoT MQTT Client Setup
AWS_MQTT_CLIENT_ID = "RaspberryPiSoilMoisture"
AWS_MQTT_TOPIC = "champlain/sensor/69/data"

# ThingsBoard MQTT Setup
THINGSBOARD_HOST = "demo.thingsboard.io"
THINGSBOARD_ACCESS_TOKEN = "ZtW5UexhXNptd2EncmXB"

def setupAWSMQTT():
    client = AWSIoTMQTTClient(AWS_MQTT_CLIENT_ID)
    client.configureEndpoint(config.AWS_HOST, config.AWS_PORT)
    client.configureCredentials(config.AWS_ROOT_CA, config.AWS_PRIVATE_KEY, config.AWS_CLIENT_CERT)
    client.configureOfflinePublishQueueing(config.OFFLINE_QUEUE_SIZE)  # Infinite offline publish queueing
    client.configureDrainingFrequency(config.DRAINING_FREQ)  # Draining frequency in Hz
    client.configureConnectDisconnectTimeout(config.CONN_DISCONN_TIMEOUT)  # 10 seconds
    client.configureMQTTOperationTimeout(config.MQTT_OPER_TIMEOUT)  # 5 seconds
    return client

def on_rpc_request(client, userdata, message):
    try:
        # Parse the RPC request
        request = json.loads(message.payload)
        method = request.get("method")
        params = request.get("params", {})

        if method == "setColor":
            color = params.get("color", "green")  # Default to green if color isn't specified
            if color == "blue":
                setColor(0x0000FF)  # Blue color
            elif color == "green":
                setColor(0x00FF00)  # Green color
            else:
                print(f"Unknown color: {color}")
        else:
            print(f"Unknown RPC method: {method}")
    except Exception as e:
        print(f"Failed to process RPC request: {e}")

def setupThingsBoard():
    client = mqtt.Client()
    client.username_pw_set(THINGSBOARD_ACCESS_TOKEN)
    client.connect(THINGSBOARD_HOST, 1883, 60)
    print("Connected to ThingsBoard MQTT broker.")
    
    # Attach the RPC request handler
    client.on_message = on_rpc_request
    client.subscribe("v1/devices/me/rpc/request/+")  # Listen for RPC requests
    
    return client

def setup(Rpin, Gpin, Bpin):
    global pins
    global p_R, p_G, p_B
    pins = {'pin_R': Rpin, 'pin_G': Gpin, 'pin_B': Bpin}
    GPIO.setmode(GPIO.BOARD)

    for i in pins:
        GPIO.setup(pins[i], GPIO.OUT)
        GPIO.output(pins[i], GPIO.HIGH)

    p_R = GPIO.PWM(pins['pin_R'], 2000)
    p_G = GPIO.PWM(pins['pin_G'], 1999)
    p_B = GPIO.PWM(pins['pin_B'], 5000)

    p_R.start(100)
    p_G.start(100)
    p_B.start(100)

    GPIO.setup(PIN_CS, GPIO.OUT)
    GPIO.output(PIN_CS, True)
    GPIO.setup(PIN_CLK, GPIO.OUT)
    GPIO.setup(PIN_DI, GPIO.OUT)
    GPIO.setup(PIN_DO, GPIO.IN)

def map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def off():
    for i in pins:
        GPIO.output(pins[i], GPIO.HIGH)

def setColor(col):
    R_val = (col & 0x00FF00) >> 16
    G_val = (col & 0x00ff00) >> 8
    B_val = (col & 0x0000ff) >> 0

    R_val = map(R_val, 0, 255, 0, 100)
    G_val = map(G_val, 0, 255, 0, 100)
    B_val = map(B_val, 0, 255, 0, 100)

    p_R.ChangeDutyCycle(100 - R_val)
    p_G.ChangeDutyCycle(100 - G_val)
    p_B.ChangeDutyCycle(100 - B_val)

def getADC(channel):
    if channel not in (0, 1):
        raise ValueError("Channel must be 0 or 1")
    GPIO.output(PIN_CS, False)
    GPIO.output(PIN_CLK, False)
    for bit in [1, 1, channel]:
        GPIO.output(PIN_DI, bool(bit))
        GPIO.output(PIN_CLK, True)
        GPIO.output(PIN_CLK, False)
    value = 0
    for _ in range(8):
        GPIO.output(PIN_CLK, True)
        GPIO.output(PIN_CLK, False)
        value <<= 1
        if GPIO.input(PIN_DO):
            value |= 0x1
    GPIO.output(PIN_CS, True)
    return value

def loop(aws_client, tb_client, moisture_threshold):
    setColor(0x00FF00)  # Initial color set to Green
    aws_client.connect()

    last_button_state = None  # Track the last state to avoid redundant updates

    while True:
        adc0 = getADC(0)
        moisture = 255 - adc0
        print(f"Moisture: {moisture}")

        # Publish moisture data to AWS and ThingsBoard
        payload = json.dumps({"moisture": moisture})
        aws_client.publish(AWS_MQTT_TOPIC, payload, 1)
        tb_client.publish("v1/devices/me/telemetry", payload)

        # Determine button state based on moisture level
        current_button_state = "On" if moisture > moisture_threshold else "Off"

        # Only send updates if the state has changed
        if current_button_state != last_button_state:
            tb_client.publish("v1/devices/me/attributes", json.dumps({"power": current_button_state}))
            print(f"Power state updated to: {current_button_state}")
            last_button_state = current_button_state

        # Force blue color when power is ON, green when OFF
        if current_button_state == "On":
            setColor(0x0000FF)  # Set blue color
        else:
            setColor(0x00FF00)  # Set green color

        time.sleep(1)

def destroy():
    p_R.stop()
    p_G.stop()
    p_B.stop()
    off()
    GPIO.cleanup()

if __name__ == "__main__":
    # Ask the user if they want to use the default threshold or input a new one
    default_threshold = 69
    user_input = input(f"The default moisture threshold is set at {default_threshold}. Do you want to continue with the default threshold? (Y/N): ").strip().lower()

    if user_input == 'n':
        try:
            moisture_threshold = int(input("Please enter a new moisture threshold: "))
        except ValueError:
            print("Invalid input. Using the default threshold.")
            moisture_threshold = default_threshold
    else:
        moisture_threshold = default_threshold

    try:
        aws_client = setupAWSMQTT()
        tb_client = setupThingsBoard()
        setup(R, G, B)
        loop(aws_client, tb_client, moisture_threshold)
    except KeyboardInterrupt:
        destroy()
        print("The end!")
