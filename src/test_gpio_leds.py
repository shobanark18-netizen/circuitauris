import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.OUT)
GPIO.setup(22, GPIO.OUT)
GPIO.setup(23, GPIO.OUT)
GPIO.setup(17, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print('Testing Green LED...')
GPIO.output(27, GPIO.HIGH)
time.sleep(1)
GPIO.output(27, GPIO.LOW)

print('Testing Red LED...')
GPIO.output(22, GPIO.HIGH)
time.sleep(1)
GPIO.output(22, GPIO.LOW)

print('Testing Yellow LED...')
GPIO.output(23, GPIO.HIGH)
time.sleep(1)
GPIO.output(23, GPIO.LOW)

print('Press the button now...')
for i in range(20):
    if GPIO.input(17) == GPIO.LOW:
        print('Button press detected!')
        break
    time.sleep(0.25)

GPIO.cleanup()
print('Done.')

