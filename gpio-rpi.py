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
gpio07_0 = GPIO(4, "in")
gpio16_1 = GPIO(23, "in")
gpio18_2 = GPIO(24, "in")
gpio19_3 = GPIO(10, "in")
gpio21_4 = GPIO(9, "in")
gpio23_5 = GPIO(11, "in")
# Open GPIO 126 with output direction
gpio26_ext = GPIO(7, "out")
gpio26_ext.write(True)

#gpio27_0 = GPIO(1, "out")
#gpio28_1 = GPIO(0, "out")

#gpio26_0 = GPIO(5, "out")
gpio29_0 = GPIO(5, "out")
gpio31_1 = GPIO(6, "out")
gpio33_2 = GPIO(13, "out")
gpio35_3 = GPIO(19, "out")
gpio37_4 = GPIO(26, "out")

def get_gpio_value():
  in_bit_0 = gpio07_0.read()
  in_bit_1 = gpio16_1.read()
  in_bit_2 = gpio18_2.read()
  in_bit_3 = gpio19_3.read()
  in_bit_4 = gpio21_4.read()
  in_bit_5 = gpio23_5.read()
  value = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3 + 16*in_bit_4 + 32*in_bit_5
  print(value)

  gpio29_0.write(in_bit_0)
  gpio31_1.write(in_bit_1)
  gpio33_2.write(in_bit_2)
  gpio35_3.write(in_bit_3)
  gpio37_4.write(in_bit_4)  
  return value

while flag:
  value = get_gpio_value()
  if(value > 0):
    print("wait for arduino")
    gpio26_ext.write(False)
    time.sleep(0.5)

    gpio26_ext.write(True)
    time.sleep(0.5)

gpio_out.write(False)
gpio_in.close()
gpio_out.close()
