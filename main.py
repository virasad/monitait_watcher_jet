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
import cv2
import numpy as np
import gauge_functions

err_msg = ""
old_err_msg = ""
image_path = ""
hostname = str(socket.gethostname())
db_connection = False
serial_connection = False
serial_rs485_connection = False
camera_connection = False
image_captured = False

# The IP camera's addresses
ip_camera_username = "admin"
ip_camera_pass = "1qaz!QAZ"
ip_camera = "192.168.101.116"
tank_diameter = 2
snapshot_url = f"rtsp://{ip_camera_username}:{ip_camera_pass}@{ip_camera}:554/cam/realmonitor?channel=1&subtype=0" 

gauge_ip_camera = "192.168.101.117"
gauge_snapshot_url = f"rtsp://{ip_camera_username}:{ip_camera_pass}@{gauge_ip_camera}:554/cam/realmonitor?channel=1&subtype=0" 

initial_tank_volume = 0
estimated_tank_volume = -1
radius = -1
tank_volume_thresholds = 20

initial_psi = 0
estimated_psi = -1
psi_thresholds = 50

try:
  dbconnect = sqlite3.connect("/home/pi/monitait_watcher_jet/monitait.db")
  cursor = dbconnect.cursor()
  db_connection = True
except:
  err_msg = err_msg + "-dbs-init"
  db_connection = False
  pass

# A function to get IP addr
def get_ip_address():
  try:
    # Create a socket connection
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Connect to an external server (doesn't have to be reachable)
    s.connect(("8.8.8.8", 80))  # Google's public DNS server
    ip_address = s.getsockname()[0]  # Get the IP address
  except Exception as e:
    err_msg = err_msg + "-unable-to-get-IP-address"
  finally:
    s.close()
  
  return ip_address

try:
  ser = serial.Serial(
        port='/dev/serial0', baudrate = 9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
  serial_connection = True
  serial_list = []
  buffer = b''
  last_received = ''
  ser.flushInput()
  extra_info = {}
  extra_info_volume = {}
  extra_info_gauge = {}
except:
  err_msg = err_msg + "-ser_init"
  serial_connection = False
  pass


try:
  video_cap = cv2.VideoCapture(snapshot_url)
  video_cap_1 = cv2.VideoCapture(snapshot_url)
        
  if video_cap.isOpened() or video_cap_1.isOpened():
    video_cap.release()
    video_cap_1.release()   
    # print("The camera is ready")
    camera_connection = True
except Exception as e:
  err_msg = err_msg + "-cam_init" + str(e)
  camera_connection = False
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
# print("Main flag", flag)
while flag:
  try:
    if (restart_counter > 1000): # check if the connection has trouble and try to solve it hard :)
      try:
        if db_connection:
          dbconnect.close()
        if serial_connection:
          ser.close()
        # if camera_connection:
        #   cam.stop()
        if serial_rs485_connection:
          ser_rs485.close()
        flag = False       
      except:
        if not("-rst" in err_msg):
          err_msg = err_msg + "-rst-" + str(e)        
        pass

    if (restart_counter > 200 and restart_counter < 204): # check if the connection has trouble and try to solve it soft
      try:
        os.system("sudo /usr/sbin/ifconfig wlan0 down && sleep 10 && sudo /usr/sbin/ifconfig wlan0 up &")
        time.sleep(20)
      except Exception as e:
        if not("-wlan" in err_msg):
          err_msg = err_msg + "-wlan-" + str(e)
        pass
      restart_counter = 204

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
    
    # Counting camera index
    j = j + 1
    print(j)
    if j % 3 == 0: 
      # Capturing image from the IP camera
      # Create the VideoCapture object with the authenticated URL
      try:
        video_cap = cv2.VideoCapture(snapshot_url)
        
        if video_cap.isOpened():
          ret, src = video_cap.read()
          video_cap.release()
          
          image_number = f"{int(time.time())}_t"
          image_path = "/home/pi/monitait_watcher_jet/" + str(image_number)
          
          # Get the original image dimensions to crop the captured image 
          height, width = 1080, 1920
          # When image size is 1920 * 880
          # left = 496
          # top = 300
          # right = 726
          # bottom = 30

          # When image size is 1920 * 1080
          left = 608
          top = 478
          right = 838
          bottom = 182
          
          # Crop 200 pixels from top and bottom the image
          # src1 = src[286:880, 498:1188]
          src1 = src[top:height-bottom, left:width-right]

          # Convert it to gray
          bg2gray = cv2.cvtColor(src1, cv2.COLOR_BGR2GRAY)

          # Reduce the noise to avoid false circle detection
          gray = cv2.medianBlur(bg2gray, 5)
          
          # Reduce the noise to avoid false circle detection
          gray = cv2.medianBlur(gray, 5)
          blurred = cv2.GaussianBlur(gray, (11, 11), 0)
          binary_thresh = cv2.threshold(blurred, 200, 255, cv2.THRESH_BINARY)[1]
          erode_thresh = cv2.erode(binary_thresh, None, iterations=2)
          thresh = cv2.dilate(erode_thresh, None, iterations=4)

          pre_rect_area, max_rect_area = -1, -1
          _, contours, hier = cv2.findContours(thresh,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
          # Finding the largest spat area
          for cnt in contours:
            current_rect_area = cv2.contourArea(cnt)
            if current_rect_area > pre_rect_area:
              max_rect_area = current_rect_area
              pre_rect_area = max_rect_area
              (x_m,y_m,w_m,h_m) = cv2.boundingRect(cnt)
                  
          # Applynig the hough circles transform 
          param2=80
          rows = gray.shape[0]
          circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 2, 15,
                                  param1=50, param2=param2, minRadius=10, maxRadius=250)
          
          k_index = 0
          # Finding possible circle 
          if circles is not None:
            circles = np.uint16(np.around(circles))
            for i_index in circles[0, :]:
              center = (i_index[0], i_index[1])
              #Checking if the found circles on the proper area
              if x_m <= center[0] <= x_m+w_m and y_m <= center[1] <= y_m+h_m:
                k_index = k_index + 1
                radius = i_index[2]
                center = center
            
            if k_index == 1:
              estimated_tank_volume = -19.95 + (1.062*radius) - 0.0034 * (radius**2)
              radius = i_index[2]
            else:
              # Applynig the hough circles transform 
              param2=80
              rows = gray.shape[0]
              
              circles_2 = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 2, 2 * rows,
                                      param1=50, param2=param2, minRadius=10, maxRadius=250)
              # Drawing the detected circles 
              if circles_2 is not None:
                circles_2 = np.uint16(np.around(circles_2))
                for i_index in circles_2[0, :]:
                  center = (i_index[0], i_index[1])
                  if x_m <= center[0] <= x_m+w_m and y_m <= center[1] <= y_m+h_m:
                    # circle outline
                    radius = i_index[2]
                            
                    # Estimation the tank height
                    estimated_tank_volume = abs(-19.95 + (1.062*radius) - 0.0034 * (radius**2))
                    
                    if estimated_tank_volume > 50:
                      estimated_tank_volume = 0
                      radius = 0
                    else:
                      pass 
                  else:
                    pass
          else:
            estimated_tank_volume = 1
            radius = 1
          
          # Writing the output image
          extra_info_volume.update({"tank_volume" : estimated_tank_volume})  
          cv2.imwrite(f"{image_path}.jpg", src)
          initial_tank_volume = estimated_tank_volume
          
          r_c_1 = watcher_update(
            register_id=hostname,
            quantity=0,
            defect_quantity=0,
            send_img=True ,
            image_path=f"{image_path}.jpg",
            product_id=0,
            lot_info=0,
            extra_info= extra_info_volume)
          print("r_c_1", r_c_1)
          if r_c_1 == requests.codes.ok: # erase files and data if it was successful   
            internet_connection = True
          else:
            internet_connection = False
          os.remove(f"{image_path}.jpg")
      except Exception as e:
        err_msg = err_msg + "-cam_read_1-" + str(e)
        pass
      
      time.sleep(2)

    # if os.path.exists(f"{image_path}.jpg"):
    #   os.remove(f"{image_path}.jpg")
    #   print(f"File {image_path} has been removed.")
    # else:
    #   print(f"File {image_path} does not exist, so no action was taken.")
    
    if j > 200:
      j=0   # reset counting index
      # Start to capture image from the Gauge
      try:
        video_cap = cv2.VideoCapture(gauge_snapshot_url)
        
        if video_cap.isOpened():
          ret, src = video_cap.read()
          video_cap.release()
          
          image_number = f"{int(time.time())}_g"
          image_path_2 = "/home/pi/monitait_watcher_jet/" + str(image_number)
          # Get the original image dimensions to crop the captured image 
          height, width, channels = src.shape
          
          # Specify the number of pixels to crop from the left and right sides
          left_crop = 100
          right_crop = 2
          bottom_crop = 700
          
          # Crop 200 pixels from top and bottom the image
          src = src[:height-bottom_crop, left_crop:width-right_crop]
          cv2.imwrite(f"{image_path_2}.jpg", src)
          gauge_number = 5
          file_type='jpg'
          
          try:
            # name the calibration image of your gauge 'gauge-#.jpg', for example 'gauge-5.jpg'.  It's written this way so you can easily try multiple images
            min_angle, max_angle, min_value, max_value, units, x, y, r = gauge_functions.calibrate_gauge(src, gauge_number, file_type)
                  

            #feed an image (or frame) to get the current value, based on the calibration, by default uses same image as calibration
            # img = cv2.imread('gauge-%s.%s' % (gauge_number, file_type))
            estimated_psi = gauge_functions.get_current_value(src, min_angle, max_angle, min_value, max_value, x, y, r, gauge_number, file_type) 
            initial_psi = abs(estimated_psi)
          except:
            estimated_psi = 0
            initial_psi = abs(estimated_psi)
          extra_info_gauge.update({"estimated_psi" : abs(estimated_psi)}) 
          
          r_c_1 = watcher_update(
            register_id=hostname+"-1",
            quantity=0,
            defect_quantity=0,
            send_img=True ,
            image_path=f"{image_path_2}.jpg",
            product_id=0,
            lot_info=0,
            extra_info= extra_info_gauge)
        
          if r_c_1 == requests.codes.ok: # erase files and data if it was successful   
            internet_connection = True
          else:
            internet_connection = False
          os.remove(f"{image_path_2}.jpg")
      except Exception as e:
        err_msg = err_msg + "-cam_read_2-" + str(e)
        pass
    
    # Reset image capturing index 
    if j > 210:
      j = 0
    else:
      pass
    
    if(temp_a + temp_b >= get_ts or i > 30): # send to the server of Monitait
      if err_msg:
        if (err_msg != old_err_msg):
          extra_info.update({"err_msg" : err_msg})  
          old_err_msg = err_msg
          err_msg = ""

      # get watcher IP addr
      local_ip = get_ip_address()
      extra_info.update({"local_ip" : local_ip})
      extra_info.update({"camera_counting_index" : j})
      i = 0 
      r_c = watcher_update(
        register_id=hostname,
        quantity=temp_a,
        defect_quantity=temp_b,
        send_img=False ,
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
              cursor.execute('''insert into monitait_table (register_id, temp_a, temp_b, image_number, extra_info) values ({},{},{},{},{})'''.format(hostname, temp_a, temp_b, image_number, json.dumps(str(extra_info)) if len(extra_info) > 0 else ""))
            else:
              cursor.execute('''insert into monitait_table (register_id, temp_a, temp_b, extra_info) values ({},{},{},{})'''.format(hostname, temp_a, temp_b, json.dumps(str(extra_info)) if len(extra_info) > 0 else ""))
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
              image_path= "/home/pi/monitait_watcher_jet/" + str(row[4] if row[4] else 0) + ".jpg",
              timestamp=datetime.datetime.strptime(row[6], '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S.%f'),
              product_id=0,
              lot_info=0,
              extra_info= json.loads(row[5].replace("'", "\"")) if len(row[5]) > 0 else None )

            if r_c == requests.codes.ok:
              sql_delete_query = """DELETE from monitait_table where id = {}""".format(row[0])      
              cursor.execute(sql_delete_query)
              dbconnect.commit()
              restart_counter = 0
              if image_captured_db:
                os.system("sudo rm -rf {}".format("/home/pi/monitait_watcher_jet/" + str(row[4]) + ".jpg"))
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