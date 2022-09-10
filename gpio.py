from periphery import GPIO
import time
import signal
import sys

flag = True

def handler(signal, frame):
  global flag
  print('handler')
  flag = False


signal.signal(signal.SIGINT, handler)
# Open GPIO 125 with input direction
gpio07_0 = GPIO(65, "in")
gpio16_1 = GPIO(101, "in")
gpio18_2 = GPIO(121, "in")
gpio19_3 = GPIO(4, "in")
gpio21_4 = GPIO(3, "in")
gpio23_5 = GPIO(2, "in")
gpio24_6 = GPIO(5, "in")
# Open GPIO 126 with output direction
gpio26_ext = GPIO(6, "out")

gpio27_0 = GPIO(1, "out")
gpio28_1 = GPIO(0, "out")
gpio29_2 = GPIO(122, "out")
gpio31_3 = GPIO(123, "out")
gpio33_4 = GPIO(124, "out")
gpio35_5 = GPIO(125, "out")
gpio37_6 = GPIO(126, "out")

while flag:
  value = gpio07_0.read() + 2*gpio16_1.read() + 4*gpio18_2.read() + 8*gpio19_3.read() + 16*gpio21_4.read() + 32*gpio23_5.read() + 64*gpio24_6.read()
  print(value)
#  gpio_out.write(value)
  time.sleep(1.0)


gpio_out.write(False)
gpio_in.close()
gpio_out.close()
