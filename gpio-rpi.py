from periphery import GPIO
import time
import signal
import sys
import requests
import json

def watcher_update(register_id, quantity, defect_quantity, product_id=0, lot_info=0, extra_info=None):
    DATA = {
        "register_id" : register_id,
        "quantity" : quantity,
        "defect_quantity": defect_quantity,
        "product_id": product_id, 
        "extra_info": extra_info,
        "lot_info": lot_info
    }
    HEADER = {
        "content-type": "application/json"
    }
    URL = "https://backend.monitait.com/api/factory/update-watcher/"
    r = requests.post(URL, data=json.dumps(DATA), headers=HEADER)
    return r.status_code, r.json()


flag = True

def handler(signal, frame):
  global flag
  print('handler')
  flag = False

i = 0 # iterator for send a dummy 0 request

signal.signal(signal.SIGINT, handler)
# Open GPIO 125 with input direction
gpio07_0 = GPIO(4, "in")
gpio16_1 = GPIO(23, "in")
gpio18_2 = GPIO(24, "in")
gpio19_3 = GPIO(10, "in")
gpio21_4 = GPIO(9, "in")
gpio23_5 = GPIO(11, "in")
# Open GPIO 126 with output direction
gpio26_ext = GPIO(8, "out")
gpio26_ext.write(False)

#gpio27_0 = GPIO(1, "out")
#gpio28_1 = GPIO(0, "out")

#gpio26_0 = GPIO(5, "out")
gpio29_0 = GPIO(5, "out")
gpio31_1 = GPIO(6, "out")
gpio33_2 = GPIO(13, "out")
gpio35_3 = GPIO(19, "out")
gpio37_4 = GPIO(26, "out")
gpio29_0.write(False)
gpio31_1.write(False)
gpio33_2.write(False)
gpio35_3.write(False)
gpio37_4.write(False)


def get_gpio_value():
  in_bit_0 = gpio07_0.read()
  in_bit_1 = gpio16_1.read()
  in_bit_2 = gpio18_2.read()
  in_bit_3 = gpio19_3.read()
  in_bit_4 = gpio21_4.read()
  in_bit_5 = gpio23_5.read()
  value = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3 + 16*in_bit_4 + 32*in_bit_5
#  print(value)

  gpio29_0.write(in_bit_0)
  gpio31_1.write(in_bit_1)
  gpio33_2.write(in_bit_2)
  gpio35_3.write(in_bit_3)
  gpio37_4.write(in_bit_4)  
  return value

while flag:
  try:
    value = get_gpio_value()
    print(value)
    if(value > 0):
      r_c, resp = watcher_update(
          register_id="1234567894",
          quantity=value,
          defect_quantity=0,
          product_id=0,
          lot_info=0,
          extra_info= {})

      print(r_c)
      if r_c == requests.codes.ok:
        print("send arduino: {}".format(value))
        gpio26_ext.write(True)
        time.sleep(0.5)
        gpio26_ext.write(False)
        i=0
    else:
      time.sleep(5)
      i=i+1
      if i > 12:
        r_c, resp = watcher_update(
          register_id="1234567894",
          quantity=0,
          defect_quantity=0,
          product_id=0,
          lot_info=0,
          extra_info= {})
        if r_c == requests.codes.ok:
          i=0
  except Exception as e:
    print("error: {}".format(str(e)))
    time.sleep(2)
    pass

gpio_out.write(False)
gpio_in.close()
gpio_out.close()
