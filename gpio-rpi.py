from periphery import GPIO
import time
import signal
import sys
import requests
import json
from requests.adapters import HTTPAdapter, Retry
import redis
import pygame
import pygame.camera

pygame.camera.init()
pygame.camera.list_cameras() #Camera detected or not
try:
  cam = pygame.camera.Camera("/dev/video0",(640,480))
except:
  cam = pygame.camera.Camera("/dev/video1",(640,480))

session = requests.Session()

r = redis.StrictRedis('localhost', 6379, charset="utf-8", decode_responses=True)

def watcher_update(register_id , quantity, defect_quantity, product_id=0, lot_info=0, extra_info=None, url = "https://app.monitait.com/api/factory/update-watcher/"):

  DATA = {
      "register_id" : register_id,
      "quantity" : quantity,
      "defect_quantity": defect_quantity,
      "product_id": product_id,
      "extra_info": extra_info,
      "lot_info": lot_info
  }
  s = requests.Session()
  retries = Retry(total=10, backoff_factor=2, ) # retry after n, 2n, 3n, 4n, 5n, ......
  s.mount(url, HTTPAdapter(max_retries=retries))
  HEADER = {
      "content-type": "application/json"
  }

  r = s.post(url, data=json.dumps(DATA), headers=HEADER)
  return r.status_code, r.json()


import requests
import json
from datetime import datetime


def watcher_update_image(session, register_id, *args, **kwargs):
    quantity = kwargs.pop("quantity", 1)
    defect_quantity = kwargs.pop("defect_quantity", 0)
    product_id = kwargs.pop("product_id", 1)
    lot_info = kwargs.pop("lot_info", 1)
    extra_info = kwargs.pop("extra_info", None)
    file_path = kwargs.pop("file_path", None)
    timestamp = kwargs.pop("timestamp", datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
    product_info = kwargs.pop("product_info", None)
        
    # try:
    DATA = {
        "register_id" : register_id,
        "quantity" : quantity,
        "defect_quantity": defect_quantity,
        "product_id": product_id, 
        "extra_info": extra_info,
        "lot_info": lot_info,
        "timestamp":timestamp, 
        "product_info":product_info
    }
    
    URL_DATA = "https://app.monitait.com/api/factory/image-update-watcher-data/"
    URL_IMAGE = "https://app.monitait.com/api/factory/image-update-watcher/"
    
    try:
        response = session.post(URL_DATA, data=json.dumps(DATA), headers={"content-type": "application/json"})
        result = response.json()
        
        if file_path is None:
            return 

        _id = result.get('_id', None)

        if _id:
            DATA = {
                'register_id':result['register_id'],
                'elastic_id':_id
            }
            print(DATA)
            
            files = {'image': open(file_path, 'rb')}
            response = session.post(URL_IMAGE, files=files, data=DATA)
            return response.json()
        
    except Exception as e:
        print(e)


def log(message):
  with open("log.log", "a") as f:
    f.write(message+"\n")

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

i=0
k=0
watcher_register_id = "12345678903"
r.set("failed_requests", 0)
file_path = 'scene.png'

try:
  while flag:
    try:
      failed_requests = int(r.get("failed_requests"))
      if ( failed_requests > 100 ):
          r.set("failed_requests", 0)
          print("reboot os due to: {}".format(str(e)))
          log(str(e))
          import os
          os.system("sudo reboot -r now")

      counter = get_gpio_value()

      if counter > 0:
          r.incrby("counter", counter)
          print("send arduino: {}".format(counter))
          gpio26_ext.write(True)
          time.sleep(0.5)
          gpio26_ext.write(False)
          i=0
          k = k+1

      else:
          time.sleep(5)
          i=i+1
          if i > 11:
              try:
                cam.start()
                img = cam.get_image()
                pygame.image.save(img, file_path)
              except:
                print("cound't capture image")

              res = watcher_update_image(
                          session=session,
                          register_id=watcher_register_id,
                          quantity=0,
                          defect_quantity=0,
                          file_path=file_path,
                          product_info={
                              "weight":100,
                              "height":200,
                              "color":254,
                              "size":400
                          }
                      ) 
                      
              print(res)

              if r_c == requests.codes.ok:
                  i=0
              else:
                  r.incr("failed_requests")


      if( k > 10):
          request_counter = int(r.get("counter"))
          r_c, resp = watcher_update(
              register_id = watcher_register_id,
              quantity=request_counter,
              defect_quantity=0)

          print("status_code", r_c," , rc", request_counter, " , response: ", resp)

          if r_c == requests.codes.ok:
              r.incrby("counter", -1 * int(request_counter) )
              k = 0
          else:
              r.incr("failed_requests")

    except Exception as e:
        print("error: {}".format(str(e)))
        log(str(e))
        time.sleep(2)
        pass

except Exception as e:
    print("reboot os due to: {}".format(str(e)))
    log(str(e))
    import os
    os.system("sudo reboot -r now")
