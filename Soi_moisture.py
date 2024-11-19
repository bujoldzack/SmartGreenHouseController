#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time

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
    R_val = (col & 0x00FF00) >> 16  # Extract Red value (0-255)
    G_val = (col & 0x00ff00) >> 8   # Extract Green value (0-255)
    B_val = (col & 0x0000ff) >> 0   # Extract Blue value (0-255)

    # Map each RGB component to a duty cycle from 0 to 100
    R_val = map(R_val, 0, 255, 0, 100)
    G_val = map(G_val, 0, 255, 0, 100)
    B_val = map(B_val, 0, 255, 0, 100)

    # Set the duty cycle for each color
    p_R.ChangeDutyCycle(100 - R_val)  # PWM: 100 means fully on, 0 means fully off
    p_G.ChangeDutyCycle(100 - G_val)
    p_B.ChangeDutyCycle(100 - B_val)

def getADC(channel):
    # Ensure the channel is valid (0 or 1)
    if channel not in (0, 1):
        raise ValueError("Channel must be 0 or 1")

    # 1. CS LOW
    GPIO.output(PIN_CS, True)  # Clear previous transmission
    GPIO.output(PIN_CS, False)  # Bring CS low

    # 2. Start clock
    GPIO.output(PIN_CLK, False)  # Start clock low

    # 3. Input MUX address
    for bit in [1, 1, channel]:  # Start bit + MUX address
        GPIO.output(PIN_DI, bool(bit))
        GPIO.output(PIN_CLK, True)
        GPIO.output(PIN_CLK, False)

    # 4. Read 8 ADC bits
    value = 0
    for _ in range(8):
        GPIO.output(PIN_CLK, True)
        GPIO.output(PIN_CLK, False)
        value <<= 1  # Shift bit
        if GPIO.input(PIN_DO):
            value |= 0x1  # Set bit if DO is HIGH

    # 5. Reset CS
    GPIO.output(PIN_CS, True)

    return value

def loop():
    setColor(0x00FF00)
    while True:
        adc0 = getADC(0)  # Read from channel 0 (soil moisture sensor)
        moisture = 255 - adc0  # Convert ADC value to moisture level
        
        print(f"Moisture: {moisture}")

        # If soil moisture is greater than 69, turn RGB to blue for 5 seconds
        if moisture > 69:
            setColor(0x0000FF)  # Set color to blue
            time.sleep(5)  # Wait for 5 seconds
            setColor(0x00FF00)  # Set color back to red
        else:
            setColor(0x00FF00)  # Default color is red
        
        time.sleep(1)

def destroy():
    p_R.stop()
    p_G.stop()
    p_B.stop()
    off()
    GPIO.cleanup()

if __name__ == "__main__":
    try:
        setup(R, G, B)
        loop()
    except KeyboardInterrupt:
        destroy()
        print("The end!")
