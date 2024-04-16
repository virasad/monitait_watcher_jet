from periphery import GPIO
import sqlite3
import time
import datetime
import signal
import requests
import json
import socket
import serial
import glob

err_msg = ""

hostname = str(socket.gethostname())

try:
  dbconnect = sqlite3.connect("monitait.db")
  cursor = dbconnect.cursor()
  db_connection = True
except:
  err_msg = err_msg + "-dbs-init"
  db_connection = False
  pass

try:
  ser = serial.Serial(
        port='/dev/serial0', baudrate = 9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
  serial_connection = True
  serial_list = []
  extra_info = {}
  i = 0
  j = 0
  buffer = b''
  last_received = ''
  ser.flushInput()

except:
  err_msg = err_msg + "-ser_init"
  serial_connection = False
  pass

try:
  if len(glob.glob("/dev/video?")) > 0:
    import pygame
    import pygame.camera
    pygame.camera.init()
    cam = pygame.camera.Camera("/dev/video0", (1280,720))
    camera_connection = True
    image_captured = False
except:
  err_msg = err_msg + "-cam_init"
  camera_connection = False
  usb_port = glob.glob("/dev/ttyUSB?") 
  if len(usb_port) > 0:
    import serial.rs485
    try:
      ser_rs485=serial.rs485.RS485(port=usb_port[0],baudrate=9600)
      ser_rs485.rs485_mode = serial.rs485.RS485Settings(False,True)
      serial_rs485_connection = True
      # ser_rs485.write('a test'.encode('utf-8'))
    except:
      err_msg = err_msg + "-rs485_init"
      serial_connection = False
      pass
  pass


def watcher_update(register_id, quantity, defect_quantity, product_id=0, lot_info=0, extra_info=None, *args, **kwargs):
    DATA = {
        "register_id" : register_id,
        "quantity" : quantity,
        "defect_quantity": defect_quantity,
        "product_id": product_id,
        "extra_info": extra_info,
        "lot_info": lot_info,
        "timestamp": kwargs.pop("timestamp", datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
    }
    HEADER = {
        "content-type": "application/json"
    }
    URL = "https://develop-app.monitait.com/api/factory/update-watcher/" #!!!!!!! take care of this develop or main API
    r = requests.post(URL, data=json.dumps(DATA), headers=HEADER)
    return r.status_code, r

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

          response = session.post(URL_IMAGE, files={"image": open("scene_image.jpg", "rb")}, data=DATA, timeout=250)
          session.close()
          return response.status_code
      session.close
      return response.status_code
  except Exception as e:
      session.close()
      return requests.codes.bad 

flag = True

def handler(signal, frame):
  global flag
  print('handler')
  flag = False

i = 0 # iterator for send a dummy 0 request
j = 0
k = 0
restart_counter = 0

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
gpio26_d.write(True) # identify the default there is no read from RPI

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
get_ts = 1
old_start_ts = time.time()
internet_connection = True
while flag:
  try:
    j = j + 1
    k = k + 1
    if (restart_counter > 500):
      try:
        if db_connection:
          dbconnect.close()
        if serial_connection:
          ser.close()
        if camera_connection:
          camera.cam.stop()
        if serial_rs485_connection:
          ser_rs485.close()
      except:
        pass

      import os
      os.system("sudo shutdown -r now")

    try:
      buffer += ser.read()
      if (b'\r\n' in buffer):
        last_received, buffer = buffer.split(b'\r\n')[-2:]
        serial_list = str(last_received).split("'")[1].split(',')
        k = 0

      if k > 1000:
        buffer = b''
        ser.flushInput()
        k = 0
        ser.sendBreak(duration = 0.02)
        time.sleep(0.2)
        ser.close()
        time.sleep(0.2)
        ser.open()

    except:
      pass

    if (j > 2500):
      try:
        cam.start()
        img = cam.get_image()
        pygame.image.save(img,"scene_image.jpg")
        cam.stop()
        image_captured = True
      except:
        image_captured = False
        pass
      for z in range(len(serial_list)):
        extra_info.update({"d{}".format(z) : int(serial_list[z])})
      r_c = watcher_update_image(
        register_id=hostname,
        quantity=0,
        defect_quantity=0,
        send_img=image_captured,
        product_id=0,
        lot_info=0,
        extra_info= extra_info)
      if r_c == requests.codes.ok:
        j=0
        internet_connection = True
        restart_counter = 0
      else:
        internet_connection = False
        restart_counter = restart_counter + 1
        time.sleep(2) 

    in_bit_a = gpio21_a.read()
    in_bit_b = gpio23_b.read()
    in_bit_0 = gpio07_0.read()
    in_bit_1 = gpio16_1.read()
    in_bit_2 = gpio18_2.read()
    in_bit_3 = gpio19_3.read()

    if in_bit_a and not(in_bit_b):
      a = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
      if (a > 0):
        set_gpio_value(a)
        gpio26_d.write(False)
        while (gpio21_a.read() != gpio23_b.read()):
          time.sleep(0.001)
        gpio26_d.write(True)
        temp_a = temp_a + a
        start_ts = time.time()
        get_ts = 10/(start_ts - old_start_ts)+0.9*get_ts
        old_start_ts = start_ts

    elif not(in_bit_a) and in_bit_b:
      b = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
      if (b > 0):
        set_gpio_value(b)
        gpio37_c.write(False) # identify it is b
        gpio26_d.write(False)
        while (gpio21_a.read() != gpio23_b.read()):
          time.sleep(0.001)
        gpio37_c.write(True) # identify default is a
        gpio26_d.write(True)
        temp_b = temp_b + b
        start_ts = time.time()
        get_ts = 10/(start_ts - old_start_ts)+0.9*get_ts
        old_start_ts = start_ts


    elif in_bit_a and in_bit_b:
      d = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
    else:
      c = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3


    if(temp_a + temp_b >= get_ts):
      if internet_connection:
        try:
          r_c, resp = watcher_update(
            register_id=hostname,
            quantity=temp_a,
            defect_quantity=temp_b,
            product_id=0,
            lot_info=0,
            extra_info= {})
          time.sleep(1)
          if r_c == requests.codes.ok:
            temp_a = 0
            temp_b = 0
            i=0
            restart_counter = 0
            internet_connection = True
          else:

            internet_connection = False

        except:
          time.sleep(1)
          pass

    else:
      time.sleep(0.1)
      i=i+1
      if i > 1200:
        try:
          r_c, resp = watcher_update(
            register_id=hostname,
            quantity=temp_a,
            defect_quantity=temp_b,
            product_id=0,
            lot_info=0,
            extra_info= {"adc" : c, "battery" : d})
          if r_c == requests.codes.ok:
            internet_connection = True
            temp_a = 0
            temp_b = 0
            restart_counter = 0
          else:
            internet_connection = False
            restart_counter  = restart_counter + 1
            try:
              if db_connection:
                cursor.execute('''insert into monitait_table ( temp_a, temp_b, c, d) values ({},{},{},{})'''.format(temp_a, temp_b, c, d))
                dbconnect.commit()
                temp_a = 0
                temp_b = 0
            except:
              restart_counter = restart_counter + 1
              pass
          i=0
        except:
          time.sleep(1)
          pass
    
    if db_connection:
      try:
        cursor.execute('SELECT * FROM monitait_table')
        output = cursor.fetchall() 
        if len(output) > 0:
          for row in output:
            print(row)
            r_c, r = watcher_update(
              register_id=hostname,
              quantity=int(row[1]),
              defect_quantity=int(row[2]),
              timestamp=datetime.datetime.strptime(row[5], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S.%f'),
              product_id=0,
              lot_info=0,
              extra_info= {"adc" : int(row[3]), "battery" : int(row[4])})
            if r_c == requests.codes.ok:
              sql_delete_query = """DELETE from monitait_table where id = {}""".format(row[0])
              cursor.execute(sql_delete_query)
              dbconnect.commit()
            else:
              time.sleep(2) 
      except Exception as f:
        print(str(f))
        pass

    time.sleep(0.01)

  except Exception as e:
    try:      
      print("error: {}".format(str(e)))
      # import os
      # os.system("sudo shutdown -r now")
      
    except:
      pass    
    time.sleep(2)
    pass
