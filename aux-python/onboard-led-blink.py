from periphery import LED
import time
import signal
import sys

flag = True

def handler(signal, frame):
  global flag
  print('handler')
  flag = False

signal.signal(signal.SIGINT, handler)
# Open On Board LED "led0" with initial state off
led0 = LED("red-flash", False)

while flag:
  led0.write(0)
  time.sleep(1.0);

  led0.write(1)
  time.sleep(1.0);

led0.close()
