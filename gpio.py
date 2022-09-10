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
gpio07_0 = GPIO(56, "in")
gpio16_1 = GPIO(101, "in")
gpio18_2 = GPIO(121, "in")
gpio19_3 = GPIO(4, "in")
gpio21_4 = GPIO(3, "in")
gpio23_5 = GPIO(2, "in")
# Open GPIO 126 with output direction
gpio24_ext = GPIO(6, "out")
gpio24_ext.write(True)

#gpio27_0 = GPIO(1, "out")
#gpio28_1 = GPIO(0, "out")
gpio26_0 = GPIO(5, "out")
gpio29_1 = GPIO(122, "out")
gpio31_2 = GPIO(123, "out")
gpio33_3 = GPIO(124, "out")
gpio35_4 = GPIO(125, "out")
gpio37_5 = GPIO(126, "out")

def get_gpio_value():
  in_bit_0 = gpio07_0.read()
  in_bit_1 = gpio16_1.read()
  in_bit_2 = gpio18_2.read()
  in_bit_3 = gpio19_3.read()
  in_bit_4 = gpio21_4.read()
  in_bit_5 = gpio23_5.read()
  value = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3 + 16*in_bit_4 + 32*in_bit_5
  print(value)
  gpio26_0.write(in_bit_0)
  gpio29_1.write(in_bit_1)
  gpio31_2.write(in_bit_2)
  gpio33_3.write(in_bit_3)
  gpio35_4.write(in_bit_4)
  gpio37_5.write(in_bit_5)  
  return value

while flag:
  value = get_gpio_value()
  if(value > 0):
    print("wait for arduino")
    gpio24_ext.write(False)
    time.sleep(1)
    gpio24_ext.write(True)
    time.sleep(1)


gpio_out.write(False)
gpio_in.close()
gpio_out.close()
