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
gpio37_c.write(False)
gpio26_d.write(False)


def get_gpio_value():
  count_a = 0
  count_b = 0
  count_c = 0
  count_d = 0
  in_bit_a = gpio21_a.read()
  in_bit_b = gpio23_b.read()
  in_bit_0 = gpio07_0.read()
  in_bit_1 = gpio16_1.read()
  in_bit_2 = gpio18_2.read()
  in_bit_3 = gpio19_3.read()

  if in_bit_a and not(in_bit_b):
    count_a = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3

  elif not(in_bit_a) and in_bit_b:
    count_b = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3

  elif in_bit_a and in_bit_b:
    count_c = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3

  else:
    count_d = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3

  return count_a, count_b, count_c, count_d

def int_to_bool_list(num):
  return [bool(num & (1<<n)) for n in range(4)]

def set_gpio_value(x):
  b_list = int_to_bool_list(x)
  gpio35_3.write(b_list[3])
  gpio33_2.write(b_list[2])
  gpio31_1.write(b_list[1])
  gpio29_0.write(b_list[0])
  return

while flag:
  try:
    a, b, c, d = get_gpio_value()
    print("a: ", a," b: ",b," c: ",c, " d: ", d)

    if(a+b > 0):
      r_c, resp = watcher_update(
          register_id=hostname,
          quantity=a,
          defect_quantity=b,
          product_id=0,
          lot_info=0,
          extra_info= {})
      if r_c == requests.codes.ok:
        if (a > 0):
          print("send arduino: a: {}".format(a))
          set_gpio_value(a)
          gpio37_c.write(True) # identify it is a
          gpio26_d.write(True)
          time.sleep(0.2)
          gpio26_d.write(False)
          time.sleep(0.2)

        if (b > 0):
          print("send arduino: b: {}".format(b))
          set_gpio_value(b)
          gpio37_c.write(False) # identify it is b
          gpio26_d.write(True)
          time.sleep(0.2)
          gpio26_d.write(False)
          time.sleep(0.2)
        i=0
    
    else:
      time.sleep(10)
      i=i+1
      if i > 12:
        r_c, resp = watcher_update(
          register_id=hostname,
          quantity=0,
          defect_quantity=0,
          product_id=0,
          lot_info=0,
          extra_info= {"adc" : c, "battery" : d})
        if r_c == requests.codes.ok:
          i=0
  except Exception as e:
    print("error: {}".format(str(e)))
    time.sleep(2)
    pass
