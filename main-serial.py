import serial
import time
import requests
import json
import socket
import pygame
import pygame.camera
import datetime

pygame.camera.init()

hostname = str(socket.gethostname())

def watcher_update_image(register_id, quantity, defect_quantity, send_img, product_id=0, lot_info=0, extra_info=None, *args, **kwargs):
    quantity = quantity
    defect_quantity = defect_quantity
    product_id = product_id
    lot_info = lot_info
    extra_info = extra_info
    timestamp = kwargs.pop("timestamp", datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
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
    session = requests.Session()
    URL_DATA = "https://app.monitait.com/api/factory/image-update-watcher-data/"
    URL_IMAGE = "https://app.monitait.com/api/factory/image-update-watcher/"
    
    try:
        response = session.post(URL_DATA, data=json.dumps(DATA), headers={"content-type": "application/json"}, timeout=150)
        result = response.json()
        _id = result.get('_id', None)
        time.sleep(1)
        if _id and send_img:
            DATA = {
                'register_id':result['register_id'],
                'elastic_id':_id
            }
            print(DATA)

            response = session.post(URL_IMAGE, files={"image": open("scene_image.jpg", "rb")}, data=DATA, timeout=250)
            session.close()
            return response.status_code
        session.close
        return response.status_code
    except Exception as e:
        print(e)
        session.close()
        return requests.codes.bad 

ser = serial.Serial(
        port='/dev/serial0', baudrate = 9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1
)
serial_list = [0,0,0,0,0,0,0,0]
i = 0
j = 0
buffer = b''
last_received = ''
ser.flushInput()
image_captured = False

while True:
  try:
    i=i+1
    j=j+1

    buffer += ser.read()
    if (b'\r\n' in buffer):
      last_received, buffer = buffer.split(b'\r\n')[-2:]
      print (last_received)
      serial_list = str(last_received).split(',')
      i = 0
      try:
        cam = pygame.camera.Camera("/dev/video0", (1280,720))
        cam.start()
        img = cam.get_image()
        pygame.image.save(img,"scene_image.jpg")
        cam.stop()
        image_captured = True
      except:
        image_captured = False
        pass

    if i > 1000:
      buffer = b''
      ser.flushInput()
      i = 0
      ser.sendBreak(duration = 0.02)
      time.sleep(0.2)
      ser.close()
      time.sleep(0.2)
      ser.open()

    if (j > 2500):
      r_c = watcher_update_image(
        register_id=hostname,
        quantity=0,
        defect_quantity=0,
        send_img=image_captured,
        product_id=0,
        lot_info=0,
        extra_info= {"serial" : str(last_received), "c" : serial_list[2], "d" : serial_list[3], "batt" : serial_list[4], "speed" : serial_list[5]})
      if r_c == requests.codes.ok:
        j=0
        internet_access = True
      else:
        internet_access = False   
        time.sleep(2) 

    time.sleep(0.001)
  except:
    time.sleep(2)
    pass
