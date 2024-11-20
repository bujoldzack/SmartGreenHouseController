#!/usr/bin/env python3
import RPi.GPIO as GPIO
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import time
import json
import config

# RGB light pins
colors = [0x00FF00, 0x0000FF]  # Red, Blue colors

R = 36
G = 38
B = 40

# Pin configuration for SPI interface
PIN_CLK = 12
PIN_DO = 13
PIN_DI = 15
PIN_CS = 11

# AWS IoT MQTT Client Setup
MQTT_CLIENT_ID = "RaspberryPiSoilMoisture"
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


def setup(Rpin, Gpin, Bpin):
    global pins
    global p_R, p_G, p_B
    pins = {'pin_R': Rpin, 'pin_G': Gpin, 'pin_B': Bpin}
    GPIO.setmode(GPIO.BOARD)  # Use physical pin numbering

    # Set up the RGB pins for PWM
    for i in pins:
        GPIO.setup(pins[i], GPIO.OUT)  # Set pins' mode to output
        GPIO.output(pins[i], GPIO.HIGH)  # Set pins to high(+3.3V) to turn off LEDs

    # Set PWM frequency for RGB pins
    p_R = GPIO.PWM(pins['pin_R'], 2000)  # Set frequency to 2KHz
    p_G = GPIO.PWM(pins['pin_G'], 1999)
    p_B = GPIO.PWM(pins['pin_B'], 5000)
    
    p_R.start(100)  # Initial duty cycle = 100 (LEDs off)
    p_G.start(100)
    p_B.start(100)

    # Set up SPI control pins (Chip Select, Clock, etc.)
    GPIO.setup(PIN_CS, GPIO.OUT)  # Ensure Chip Select pin is set as output
    GPIO.output(PIN_CS, True)  # Initialize Chip Select as HIGH (inactive)
    GPIO.setup(PIN_CLK, GPIO.OUT)  # Set Clock pin as output
    GPIO.setup(PIN_DI, GPIO.OUT)  # Set Data In pin as output
    GPIO.setup(PIN_DO, GPIO.IN)   # Set Data Out pin as input

def map(x, in_min, in_max, out_min, out_max):
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def off():
    for i in pins:
        GPIO.output(pins[i], GPIO.HIGH)  # Turn off all LEDs

def setColor(col):  # For example: col = 0x112233
    R_val = (col & 0x00FF00) >> 16
    G_val = (col & 0x00ff00) >> 8
    B_val = (col & 0x0000ff) >> 0

    R_val = map(R_val, 0, 255, 0, 100)
    G_val = map(G_val, 0, 255, 0, 100)
    B_val = map(B_val, 0, 255, 0, 100)

    p_R.ChangeDutyCycle(100 - R_val)  # Change duty cycle
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

def loop(mqtt_client):
    setColor(0x00FF00)
    mqtt_client.connect()
    while True:
        adc0 = getADC(0)
        moisture = 255 - adc0
        print(f"Moisture: {moisture}")

        # Publish moisture data to MQTT
        payload = json.dumps({"moisture": moisture})
        mqtt_client.publish(MQTT_TOPIC, payload, 1)

        # Set color based on moisture level
        if moisture > 69:
            setColor(0x0000FF)
            time.sleep(5)
            setColor(0x00FF00)
        else:
            setColor(0x00FF00)
        
        time.sleep(1)

def destroy():
    p_R.stop()
    p_G.stop()
    p_B.stop()
    off()
    GPIO.cleanup()

if __name__ == "__main__":
    try:
        mqtt_client = setupMQTT()
        setup(R, G, B)
        loop(mqtt_client)
    except KeyboardInterrupt:
        destroy()
        print("The end!")
