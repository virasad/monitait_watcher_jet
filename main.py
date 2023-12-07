from periphery import GPIO
import time
import signal
import sys
import requests
import json
import socket
hostname = str(socket.gethostname())

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
    URL = "https://app.monitait.com/api/factory/update-watcher/"
    r = requests.post(URL, data=json.dumps(DATA), headers=HEADER)
    return r.status_code, r #.json()


flag = True

def handler(signal, frame):
  global flag
  print('handler')
  flag = False

i = 0 # iterator for send a dummy 0 request

signal.signal(signal.SIGINT, handler)
gpio07_0 = GPIO(4, "in")
gpio16_1 = GPIO(23, "in")
gpio18_2 = GPIO(24, "in")
gpio19_3 = GPIO(10, "in")

gpio29_0 = GPIO(5, "out")
gpio31_1 = GPIO(6, "out")
gpio33_2 = GPIO(13, "out")
gpio35_3 = GPIO(19, "out")

gpio29_0.write(False)
gpio31_1.write(False)
gpio33_2.write(False)
gpio35_3.write(False)

gpio21_a = GPIO(9, "in")
gpio23_b = GPIO(11, "in")

gpio37_c = GPIO(26, "out")
gpio26_d = GPIO(8, "out")
gpio37_c.write(True) # identify default is a
gpio26_d.write(False)

def int_to_bool_list(num):
  return [bool(num & (1<<n)) for n in range(4)]

def set_gpio_value(x):
  b_list = int_to_bool_list(x)
  gpio35_3.write(b_list[3])
  gpio33_2.write(b_list[2])
  gpio31_1.write(b_list[1])
  gpio29_0.write(b_list[0])
  return

temp_a = 0
temp_b = 0
a = 0
b = 0
c = 0
d = 0
internet_access = True
while flag:
  try:

    in_bit_a = gpio21_a.read()
    in_bit_b = gpio23_b.read()
    in_bit_0 = gpio07_0.read()
    in_bit_1 = gpio16_1.read()
    in_bit_2 = gpio18_2.read()
    in_bit_3 = gpio19_3.read()

    if in_bit_a and not(in_bit_b):
      a = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
      if (a > 0 and internet_access):
        set_gpio_value(a)
        gpio26_d.write(True)
        while (gpio21_a.read() != gpio23_b.read()):
          time.sleep(0.001)
        gpio26_d.write(False)
        temp_a = temp_a + a

    elif not(in_bit_a) and in_bit_b:
      b = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
      if (b > 0 and internet_access):
        set_gpio_value(b)
        gpio37_c.write(False) # identify it is b
        gpio26_d.write(True)
        while (gpio21_a.read() != gpio23_b.read()):
          time.sleep(0.001)
        gpio37_c.write(True) # identify default is a
        gpio26_d.write(False)
        temp_b = temp_b + b

    elif in_bit_a and in_bit_b:
      c = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3

    else:
      d = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3

    if(temp_a + temp_b >= 100):
      r_c, resp = watcher_update(
          register_id=hostname,
          quantity=temp_a,
          defect_quantity=temp_b,
          product_id=0,
          lot_info=0,
          extra_info= {})
      if r_c == requests.codes.ok:
        temp_a = temp_a - temp_a
        temp_b = temp_b - temp_b
        i=0
        internet_access = True
      else:
        internet_access = False

    else:
      time.sleep(0.1)
      i=i+1
      if i > 1200:
        r_c, resp = watcher_update(
          register_id=hostname,
          quantity=temp_a,
          defect_quantity=temp_b,
          product_id=0,
          lot_info=0,
          extra_info= {"adc" : c, "battery" : d})
        if r_c == requests.codes.ok:
          print("liveniness server: {},{},{},{}".format(temp_a, temp_b,c,d))
          temp_a = temp_a - temp_a
          temp_b = temp_b - temp_b
          i=0
          internet_access = True
        else:
          internet_access = False

  except Exception as e:
    print("error: {}".format(str(e)))
    time.sleep(2)
    pass
