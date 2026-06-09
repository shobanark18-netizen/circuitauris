import RPi.GPIO as GPIO
import time

# Pin definitions
GREEN_LED = 27
RED_LED = 22
YELLOW_LED = 23
BUTTON = 17

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(GREEN_LED, GPIO.OUT)
GPIO.setup(RED_LED, GPIO.OUT)
GPIO.setup(YELLOW_LED, GPIO.OUT)
GPIO.setup(BUTTON, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def blink(pin, times=3, delay=0.3):
    for _ in range(times):
        GPIO.output(pin, True)
        time.sleep(delay)
        GPIO.output(pin, False)
        time.sleep(delay)

print("Testing GREEN LED...")
blink(GREEN_LED)

print("Testing RED LED...")
blink(RED_LED)

print("Testing YELLOW LED...")
blink(YELLOW_LED)

print("All LEDs tested. Press button to test...")

try:
    while True:
        if not GPIO.input(BUTTON):
            print("Button pressed!")
            GPIO.output(GREEN_LED, True)
            time.sleep(0.5)
            GPIO.output(GREEN_LED, False)
        time.sleep(0.05)

except KeyboardInterrupt:
    print("Test complete")
    GPIO.cleanup()