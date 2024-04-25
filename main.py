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
import os

err_msg = ""
image_path = ""
hostname = str(socket.gethostname())
db_connection = False
serial_connection = False
serial_rs485_connection = False
camera_connection = False
image_captured = False

try:
  dbconnect = sqlite3.connect("/home/pi/monitait_watcher_jet/monitait.db")
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
    cam = pygame.camera.Camera("/dev/video0")
    camera_connection = True
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
      serial_rs485_connection = False
      pass
  pass

def watcher_update(register_id, quantity, defect_quantity, send_img, image_path="scene_image.jpg", product_id=0, lot_info=0, extra_info=None, *args, **kwargs):
  quantity = quantity
  defect_quantity = defect_quantity
  product_id = product_id
  lot_info = lot_info
  extra_info = extra_info
  timestamp = kwargs.pop("timestamp", datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
  product_info = kwargs.pop("product_info", None)

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

  URL = "https://app.monitait.com/api/factory/update-watcher/" # send data without waiting for elastic id
  URL_DATA = "https://app.monitait.com/api/factory/image-update-watcher-data/" # send data and get elastic id
  URL_IMAGE = "https://app.monitait.com/api/factory/image-update-watcher/" # send image based on elastic id
  
  try:
    if send_img:
      response = session.post(URL_DATA, data=json.dumps(DATA), headers={"content-type": "application/json"}, timeout=150)
      result = response.json()
      _id = result.get('_id', None)
      time.sleep(1)
      if _id:
          DATA = {
              'register_id':result['register_id'],
              'elastic_id':_id
          }

          response = session.post(URL_IMAGE, files={"image": open(image_path, "rb")}, data=DATA, timeout=250)
          session.close()
          return response.status_code
      session.close
      return response.status_code
    else:
      response = requests.post(URL, data=json.dumps(DATA), headers={"content-type": "application/json"})
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
    if restart_counter > 4010:
      flag = False

    if (restart_counter > 4000): # check if the connection has trouble and try to solve it hard :)
      try:
        if db_connection:
          dbconnect.close()
        if serial_connection:
          ser.close()
        if camera_connection:
          cam.stop()
        if serial_rs485_connection:
          ser_rs485.close()
        os.system("sudo shutdown -r now")        
      except:
        pass

    if (restart_counter > 2000 and restart_counter < 2040): # check if the connection has trouble and try to solve it soft
      try:
        os.system("sudo /usr/sbin/ifconfig wlan0 down && sleep 10 && sudo /usr/sbin/ifconfig wlan0 up &")
        time.sleep(20)
      except Exception as e:
        if not("-wlan" in err_msg):
          err_msg = err_msg + "-wlan-" + str(e)
        pass
      restart_counter = 2040

    try:
      k = k + 1
      for x in range(100):
        if ( x % 30 == 0 and serial_connection): # read serial data
          buffer += ser.read(2000)
          time.sleep(0.01)
          if (b'\r\n' in buffer): # find line in serial data
            last_received, buffer = buffer.split(b'\r\n')[-2:]
            serial_list = str(last_received).split("'")[1].split(',')
            for z in range(len(serial_list)):
              extra_info.update({"d{}".format(z) : int(serial_list[z])})
            k = 0
            i = i + 1
        in_bit_a = gpio21_a.read() # read arduino data
        in_bit_b = gpio23_b.read()
        in_bit_0 = gpio07_0.read()
        in_bit_1 = gpio16_1.read()
        in_bit_2 = gpio18_2.read()
        in_bit_3 = gpio19_3.read()

        if in_bit_a and not(in_bit_b): # read arduino data a (OK)
          a = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
          if (a > 0):
            set_gpio_value(a)
            gpio26_d.write(False)
            while (gpio21_a.read() != gpio23_b.read()):
              time.sleep(0.001)
            gpio26_d.write(True)
            temp_a = temp_a + a
            start_ts = time.time()
            get_ts = 1/(start_ts - old_start_ts)+0.9*get_ts
            old_start_ts = start_ts

        elif not(in_bit_a) and in_bit_b: # read arduino data b (NG)
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
            get_ts = 1/(start_ts - old_start_ts)+0.9*get_ts
            old_start_ts = start_ts
        elif in_bit_a and in_bit_b: # read arduino data d (A7 in 15 levels [0..15])
          d = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
        else:                       # read arduino data c (A5 in 15 levels [0..15])
          c = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3


      if ( k > 1000 and serial_connection) : # restart serial input if stuck
        buffer = b''
        ser.flushInput()
        k = 0
        ser.sendBreak(duration = 0.02)
        time.sleep(0.2)
        ser.close()
        time.sleep(0.2)
        ser.open()
    except Exception as e:
      if not("-sergpio_read" in err_msg):
        err_msg = err_msg + "-sergpio_read-" + str(e)
      pass

    if camera_connection:
      j = j + 1

    if (j > 20): # capture image every 300sec
      try:
        cam.start()
        img = cam.get_image()
        image_number = int(time.time())
        image_path = "/home/pi/monitait_watcher_jet/" + str(image_number) + ".jpg"
        pygame.image.save(img,image_path)
        cam.stop()
        image_captured = True
      except Exception as e:
        image_captured = False
        if not("-cam_read" in err_msg):
          err_msg = err_msg + "-cam_read-" + str(e)
        if len(glob.glob("/dev/video?")) > 0:
          pygame.camera.init()
          cam = pygame.camera.Camera("/dev/video0")
          camera_connection = True
        pass
      j=0

    if(temp_a + temp_b >= get_ts or i > 20 or image_captured): # send to the server of Monitait
      if err_msg:
        extra_info.update({"err_msg" : err_msg})
        err_msg = ""

      i = 0 
      r_c = watcher_update(
        register_id=hostname,
        quantity=temp_a,
        defect_quantity=temp_b,
        send_img=image_captured,
        image_path=image_path,
        product_id=0,
        lot_info=0,
        extra_info= extra_info)
      if r_c == requests.codes.ok: # erase files and data if it was successful
        temp_a = 0
        temp_b = 0
        internet_connection = True
        restart_counter = 0
        extra_info.pop("err_msg", None)
        if image_captured:
          os.system("sudo rm -rf {}".format(image_path))
          image_captured = False
      else:                        # insert files and data if it fails to send data to the server
        internet_connection = False
        try:
          if db_connection:
            if image_captured:
              cursor.execute('''insert into monitait_table (register_id, temp_a, temp_b, image_number, extra_info) values ({},{},{},{},{})'''.format(hostname, temp_a, temp_b, image_number, repr(extra_info)))
            else:
              cursor.execute('''insert into monitait_table (register_id, temp_a, temp_b, extra_info) values ({},{},{},{})'''.format(hostname, temp_a, temp_b, repr(extra_info)))
            dbconnect.commit()
            temp_a = 0
            temp_b = 0
            extra_info.pop("err_msg", None)
            restart_counter = restart_counter + 1
            
          else:
            restart_counter = restart_counter + 4
            if image_captured:
              os.system("sudo rm -rf {}".format(image_path))
              image_captured = False

        except Exception as e:
          if not("-db_insrt" in err_msg):
            err_msg = err_msg + "-db_insrt-" + str(e)
          if image_captured:
            os.system("sudo rm -rf {}".format(image_path))
            image_captured
          restart_counter = restart_counter + 4
          pass


    if db_connection and internet_connection: # resend files and data if it there is any data in database
      try:
        cursor.execute('SELECT * FROM monitait_table LIMIT 5')
        output = cursor.fetchall() 
        if len(output) > 0:
          for row in output:
            if row[4]:
              image_captured_db = True
            else:
              image_captured_db = False
            r_c= watcher_update(
              register_id=row[1],
              quantity=int(row[2]),
              defect_quantity=int(row[3]),
              send_img=image_captured_db,
              image_path= "/home/pi/monitait_watcher_jet/" + str(row[4]) + ".jpg",
              timestamp=datetime.datetime.strptime(row[6], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S.%f'),
              product_id=0,
              lot_info=0,
              extra_info= eval(row[5]))

            if r_c == requests.codes.ok:
              sql_delete_query = """DELETE from monitait_table where id = {}""".format(row[0])      
              cursor.execute(sql_delete_query)
              dbconnect.commit()
              restart_counter = 0
              if image_captured_db:
                os.system("sudo rm -rf {}".format("/home/pi/monitait_watcher_jet/" + row[4]))
            else:
              internet_connection = False

      except Exception as e:
        if not("-db_slct" in err_msg):
          err_msg = err_msg + "-db_slct-" + str(e)
        pass

    time.sleep(0.001)

  except Exception as e:
    if not("-ftl" in err_msg):
      err_msg = err_msg + "-ftl-" + str(e)
    pass