from gpiozero import InputDevice
from gpiozero import LED
import sqlite3
import time
import datetime
import signal
import requests
import json
import socket
import serial
import os
import cv2
from threading import Thread
import evdev
import logging


date = datetime.datetime.now()
date_hour, date_minute, date_second = time.strftime("%H"), time.strftime("%M"), time.strftime("%S")
watcher_date_log = f"{date.year}_{date.month}_{date.day}_{date_hour}_{date_minute}_{date_second}"

for handler in logging.root.handlers[:]:
  logging.root.removeHandler(handler)

logging.basicConfig(
  filename=f"/home/pi/monitait_watcher_jet/watcher_{watcher_date_log}.log",
  format="%(asctime)s:%(levelname)s:%(message)s",
  filemode='a',
  datefmt='%H:%M:%S',
  level=logging.INFO
)


hostname = str(socket.gethostname())

def watcher_update(register_id, quantity, defect_quantity, send_img, image_path="scene_image.jpg", product_id=0, lot_info=0, extra_info=None, timestamp=datetime.datetime.utcnow(), *args, **kwargs):
    quantity = quantity
    defect_quantity = defect_quantity
    product_id = product_id
    lot_info = lot_info
    extra_info = extra_info
    timestamp = timestamp.strftime('%Y-%m-%dT%H:%M:%S.%f')
    product_info = kwargs.pop("product_info", None)

    DATA = {
        "register_id" : register_id,
        "quantity" : quantity,
        "defect_quantity": defect_quantity,
        "product_id": product_id, 
        "extra_info": extra_info if extra_info else {},
        "lot_info": lot_info,
        "timestamp":timestamp, 
        "product_info":product_info
        }
    # print(DATA)
    session = requests.Session()

    URL = "https://app.monitait.com/api/factory/update-watcher/" # send data without waiting for elastic id
    URL_DATA = "https://app.monitait.com/api/factory/image-update-watcher-data/" # send data and get elastic id
    URL_IMAGE = "https://app.monitait.com/api/factory/image-update-watcher/" # send image based on elastic id
    
    try:
        if send_img:
            try:
                response = session.post(URL_DATA, data=json.dumps(DATA), headers={"content-type": "application/json"}, timeout=150)
                result = response.json()
                _id = result.get('_id', None)
                time.sleep(1)
                if _id:
                    DATA = {
                        'register_id':result['register_id'],
                        'elastic_id':_id
                        }
                    try:
                        response = session.post(URL_IMAGE, files={"image": open(image_path, "rb")}, data=DATA, timeout=250)
                        session.close()
                        if (response.status_code == requests.codes.ok):
                            os.remove(image_path)
                            return True
                        else:
                            return False    
                    except Exception as e:
                        return False
                else:
                    session.close()
                    return False
            except Exception as e:
                # print(f"watcher update image {e}")
                return False
        else:
            try:
                response = requests.post(URL, data=json.dumps(DATA), headers={"content-type": "application/json"})
                logging.info(f"\n post data, response status code {response.status_code}")
                # print(response.text, "code:", response.status_code)
                if (response.status_code == requests.codes.ok):
                    return True
                else:
                    return False
            except Exception as e:
                # print(f"watcher update no image {e}")
                logging.info(f"\n watcher update no image {e}")
                return False
    except Exception as e:
        logging.info(f"\n session going to close {e}")
        session.close()
        return False

class DB:
    def __init__(self) -> None:
        try:
            self.dbconnect = sqlite3.connect("/home/pi/monitait_watcher_jet/monitait.db", check_same_thread=False)
            self.cursor = self.dbconnect.cursor()
            self.db_connection = True
            self.cursor.execute('''create table monitait_table (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, register_id TEXT, temp_a INTEGER NULL, temp_b INTEGER NULL, image_name TEXT NULL, extra_info JSON, ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL)''')
            self.dbconnect.commit()
        except Exception as e:
            logging.info(f"\n DB init {e}")
            pass
            # print(f"DB > init {e}")


    def write(self, register_id=hostname, a=0, b=0, extra_info={}, image_name="", timestamp=datetime.datetime.utcnow()):
        try:
            self.cursor.execute('''insert into monitait_table (register_id, temp_a, temp_b, image_name, extra_info, ts) values (?,?,?,?,?,?)''', (register_id, a, b, image_name, json.dumps(extra_info), timestamp))
            self.dbconnect.commit()
            return True
        except Exception as e:
            logging.info(f"\n DB write {e}")
            # print(f"DB > write {e}")
            return False

    def read(self):
        try:
            self.cursor.execute('SELECT * FROM monitait_table LIMIT 1')
            rows = self.cursor.fetchall()
            if len(rows) != 0:
              return rows[0]
            else:
              return []
        except Exception as e:
            logging.info(f"\n DB read {e}")
            # print(f"DB > read {e}")
            return []

    def delete(self, id):
        try:
            self.cursor.execute("""DELETE from monitait_table where id = {}""".format(id))
            self.dbconnect.commit()
            return True
        except Exception as e:
            logging.info(f"\n DB delete {e}") 
            # print(f"DB > delete {e}")
            return False

class Ardiuno:
    def __init__(self) -> None:
        self.stop_thread = False
        self.last_a = 0
        self.last_b = 0
        self.c = 0
        self.d = 0
        self.i = 0 # iterator for send a dummy 0 request
        self.j = 0
        self.k = 0
        self.retry_timeout_connect_serial = 1
        self.restart_counter = 0
        self.gpio16_0 = InputDevice(23) # Address pin for DIP switch 3
        self.gpio18_0 = InputDevice(24) # Address pin for DIP switch 4
        self.watcher_mode = 1*self.gpio16_0.value + 2*self.gpio18_0.value
        # input a, b, c, d data from arduino
        self.gpio07_0 = InputDevice(4) # same
        self.gpio19_1 = InputDevice(10) # same
        self.gpio35_2 = InputDevice(19) # same

        self.gpio36_0 = InputDevice(16) # same

        # send a, b , c, d data to arduino
        self.gpio29_0 = LED(5) # same
        self.gpio31_1 = LED(6) # same
        self.gpio33_2 = LED(13) # same
        self.gpio29_0.off() # default all zero
        self.gpio31_1.off() # default all zero
        self.gpio33_2.off() # default all zero

        self.gpio21_a = InputDevice(9) #same
        self.gpio23_b = InputDevice(11) #same
        self.gpio37_c = LED(26) #same
        self.gpio26_d = LED(8) # same

        self.gpio11_0 = LED(17) # DE/RE
        self.gpio13_0 = LED(27) # RS485 TX
        self.gpio15_0 = InputDevice(22) # RS485 RX

        self.gpio32_0 = LED(12) # Buzzer
        self.gpio32_0.on() # it is high by default and should goes down in case of buzz

        self.gpio37_c.on() # identify default is a
        self.gpio26_d.on() # identify as the default there is no read from RPI
        self.get_ts = 1
        self.buffer = b''
        self.serial_connection = self.open_serial()
        Thread(target=self.run_GPIO).start()
        Thread(target=self.run_serial).start()

    def open_serial(self):
        try:
            self.ser = serial.Serial(
                    port='/dev/serial0', baudrate = 9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
            self.serial_list = []
            self.buffer = b''
            self.last_received = ''
            self.ser.flushInput()
            self.serial_data = {}
            return True
        except Exception as e:
            logging.info(f"\n serial 0 exception {e}")
            try:
                self.ser = serial.Serial(
                    port='/dev/serial1', baudrate = 9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
                self.serial_list = []
                self.buffer = b''
                self.last_received = ''
                self.ser.flushInput()
                self.extra_info = {}
                return True
            except Exception as ee:
                logging.info(f"\n serial 1 exception {ee}")
                # print(e)
                return False

    def close_serial(self):

        try:
            if self.serial_connection:
                self.ser.close()
            return True
        except Exception as e:
            logging.info(f"\n close serial exception {e}")
            # print(e)
            return False

    def int_to_bool_list(self, num):
        return [bool(num & (1<<n)) for n in range(4)]

    def set_gpio_value(self, x):
        b_list = self.int_to_bool_list(x)
        self.gpio33_2.value = b_list[2]
        self.gpio31_1.value = b_list[1]
        self.gpio29_0.value = b_list[0]
        
    def run_serial(self):
        if self.serial_connection:
            while not self.stop_thread:
                try:
                    tmp_serial_data = {}
                    self.buffer += self.ser.read(2000)
                    # self.ser.write("1\n".encode('utf-8'))
                    # time.sleep(1)
                    # self.ser.write("2\n".encode('utf-8'))
                    # time.sleep(1)
                    # self.ser.write("8\n".encode('utf-8'))
                    # time.sleep(0.01)
                    if (b'\r\n' in self.buffer): # find line in serial data
                        last_received, self.buffer = self.buffer.split(b'\r\n')[-2:]
                        serial_list = str(last_received).split("'")[1].split(',')
                        for z in range(len(serial_list)):
                            tmp_serial_data.update({"d{}".format(z) : int(serial_list[z])})
                        self.serial_data = tmp_serial_data
                    time.sleep(0.01)

                except Exception as e:
                    logging.info(f"\n arduino Serial reader {e}")
                    if "Input/output" in str(e):
                        try:
                            self.close_serial()
                            time.sleep()
                            self.open_serial()
                        except Exception as er:
                            pass
                            # print(er)
                    if "fileno" in str(e):
                        try:
                            self.close_serial()
                            self.open_serial()
                        except Exception as ers:
                            pass
                            # print(ers)
                    # print(f"arduino Serial reader {e}")
        else:
            if self.retry_timeout_connect_serial < 4096:
                self.retry_timeout_connect_serial = self.retry_timeout_connect_serial * 2
                self.serial_connection = self.open_serial()
            else:
                self.retry_timeout_connect_serial = 4096
            time.sleep(self.retry_timeout_connect_serial)
            return None

    def run_GPIO(self):
        self.old_start_ts = time.time()
        while not self.stop_thread:
            try:
                in_bit_a = self.gpio21_a.value # read arduino a,b address
                in_bit_b = self.gpio23_b.value

                in_bit_0 = self.gpio07_0.value # read arduino data
                in_bit_1 = self.gpio19_1.value
                in_bit_2 = self.gpio35_2.value

                a = 0
                b = 0
                if in_bit_a and not(in_bit_b): # read arduino data a (OK)
                    a = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2

                if (a > 0):
                    self.set_gpio_value(a)
                    self.gpio37_c.on() # identify it is a
                    self.gpio26_d.off()
                    while (self.gpio21_a.value != self.gpio23_b.value):
                        time.sleep(0.001)
                    self.gpio26_d.on()
                    self.last_a += a
                    start_ts = time.time()
                    self.get_ts = 1/(start_ts - self.old_start_ts)+0.9*self.get_ts
                    self.old_start_ts = start_ts

                elif not(in_bit_a) and in_bit_b: # read arduino data b (NG)
                    b = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2
                if (b > 0):
                    self.set_gpio_value(b)
                    self.gpio37_c.off() # identify it is b
                    self.gpio26_d.off()
                    while (self.gpio21_a.value != self.gpio23_b.value):
                        time.sleep(0.001)
                    self.gpio37_c.on() # identify default is a
                    self.gpio26_d.on()
                    self.last_b += b
                    start_ts = time.time()
                    self.get_ts = 1/(start_ts - self.old_start_ts)+0.9*self.get_ts
                    self.old_start_ts = start_ts
                elif in_bit_a and in_bit_b: # read arduino battery (A6 in 8 levels [0..7])
                    self.d = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2
                else:                       # read arduino data c (A7 in 8 levels [0..7])
                    self.c = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2
                # print(self.last_a,self.last_b,self.c,self.d)
                time.sleep(0.01)
            except Exception as e:
                logging.info(f"\n arduino GPIO reader {e}")
                pass
                # print(f"arduino GPIO reader {e}")


    def read_GPIO(self):
        return self.last_a, self.last_b, self.c, self.d , self.get_ts

    def minus(self, a, b):
        self.last_a -= a
        self.last_b -= b

    def read_serial(self):
        return self.serial_data

class Camera:
    def __init__(self, fps=30, exposure=100, gain=1, gamma=1, contrast=3, roi=[0,0,1920,1080], temperature=5000, brightness=1, step=10, auto_exposure=3) -> None:
        self.camera_id = 0
        self.fps = fps
        self.fourcc = 0x47504A4D
        self.frame_width = abs(roi[2] - roi[0])
        self.frame_height = abs(roi[3] - roi[1])
        self.exposure = exposure
        self.gain = gain
        self.contrast = contrast
        self.gamma = gamma
        self.roi = roi
        self.auto_exposure = auto_exposure
        self.temperature = temperature
        self.brightness = brightness
        self.video_cap = self.camera_setup()
        self.frames = 0
        self.stop_thread = False
        self.success = False
        self.step = step
        success, frame = self.video_cap.read()
        if success:
            self.frame = frame[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
            # print([self.roi[1], self.roi[3], self.roi[0], self.roi[2]])
        else:
            self.frame = frame
        self.success = success
        Thread(target=self._reader).start()
        self.crop_list = [0, self.roi[3] - self.roi[1], 0, self.roi[2] - self.roi[0]]

    def _reader(self):
        while not self.stop_thread:
            health_count = 0
            try:
                success, frame = self.video_cap.read()
                # print(f"camera {success}")
                if success:
                    self.frame = frame[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
                    self.success = success
                    health_count = 0
                else:
                    health_count += 1
                    if health_count > 100:
                        try:
                            self.release_camera()
                        except:
                            pass 
                        self.video_cap = self.camera_setup()
                        success, frame = self.video_cap.read()
                        self.frame = frame[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
                        self.success = success
                        health_count = 0
                time.sleep(0.1)
            except:
                logging.info(f"\n stop thread exception {e}")
                time.sleep(0.1)
                pass

    def read(self):
        return self.frame

    def camera_setup(self):
        video_cap = cv2.VideoCapture(os.path.realpath(f"/dev/video{self.camera_id}"))
        video_cap.set(cv2.CAP_PROP_FPS, self.fps)
        video_cap.set(cv2.CAP_PROP_FOURCC, self.fourcc)
        video_cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        video_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        video_cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, self.auto_exposure)
        video_cap.set(cv2.CAP_PROP_AUTO_WB, 0.0)
        video_cap.set(cv2.CAP_PROP_WB_TEMPERATURE, self.temperature)
        video_cap.set(cv2.CAP_PROP_BRIGHTNESS, self.brightness)
        video_cap.set(cv2.CAP_PROP_EXPOSURE, self.exposure)
        video_cap.set(cv2.CAP_PROP_GAIN, self.gain)
        video_cap.set(cv2.CAP_PROP_CONTRAST, self.contrast)
        return video_cap

    def capture_and_save(self):

        if self.success:
            im = self.read()
            date = datetime.datetime.utcnow()
            saving_date = f"{date.year}-{date.month}-{date.day}-{date.hour}-{date.minute}-{date.second}-{date.microsecond}"
            os.makedirs("images", exist_ok=True)
            image_name = f"images/{saving_date}.jpg"

            cv2.imwrite(image_name, im)
            return True, image_name
        return False, ""

    def release_camera(self):
        self.video_cap.release()

class Scanner:
    def __init__(self, fps=30, exposure=100, gain=1, gamma=1, contrast=3, roi=[0,0,1920,1080], temperature=5000, brightness=1, step=10, auto_exposure=3) -> None:
        self.VENDOR_PRODUCT = [
        [0xac90, 0x3002], # [vendor, product]
        ]
        self.CHARMAP = {
        evdev.ecodes.KEY_1: ['1', '!'],
        evdev.ecodes.KEY_2: ['2', '@'],
        evdev.ecodes.KEY_3: ['3', '#'],
        evdev.ecodes.KEY_4: ['4', '$'],
        evdev.ecodes.KEY_5: ['5', '%'],
        evdev.ecodes.KEY_6: ['6', '^'],
        evdev.ecodes.KEY_7: ['7', '&'],
        evdev.ecodes.KEY_8: ['8', '*'],
        evdev.ecodes.KEY_9: ['9', '('],
        evdev.ecodes.KEY_0: ['0', ')'],
        evdev.ecodes.KEY_MINUS: ['-', '_'],
        evdev.ecodes.KEY_EQUAL: ['=', '+'],
        evdev.ecodes.KEY_TAB: ['\t', '\t'],
        evdev.ecodes.KEY_Q: ['q', 'Q'],
        evdev.ecodes.KEY_W: ['w', 'W'],
        evdev.ecodes.KEY_E: ['e', 'E'],
        evdev.ecodes.KEY_R: ['r', 'R'],
        evdev.ecodes.KEY_T: ['t', 'T'],
        evdev.ecodes.KEY_Y: ['y', 'Y'],
        evdev.ecodes.KEY_U: ['u', 'U'],
        evdev.ecodes.KEY_I: ['i', 'I'],
        evdev.ecodes.KEY_O: ['o', 'O'],
        evdev.ecodes.KEY_P: ['p', 'P'],
        evdev.ecodes.KEY_LEFTBRACE: ['[', '{'],
        evdev.ecodes.KEY_RIGHTBRACE: [']', '}'],
        evdev.ecodes.KEY_A: ['a', 'A'],
        evdev.ecodes.KEY_S: ['s', 'S'],
        evdev.ecodes.KEY_D: ['d', 'D'],
        evdev.ecodes.KEY_F: ['f', 'F'],
        evdev.ecodes.KEY_G: ['g', 'G'],
        evdev.ecodes.KEY_H: ['h', 'H'],
        evdev.ecodes.KEY_J: ['j', 'J'],
        evdev.ecodes.KEY_K: ['k', 'K'],
        evdev.ecodes.KEY_L: ['l', 'L'],
        evdev.ecodes.KEY_SEMICOLON: [';', ':'],
        evdev.ecodes.KEY_APOSTROPHE: ['\'', '"'],
        evdev.ecodes.KEY_BACKSLASH: ['\\', '|'],
        evdev.ecodes.KEY_Z: ['z', 'Z'],
        evdev.ecodes.KEY_X: ['x', 'X'],
        evdev.ecodes.KEY_C: ['c', 'C'],
        evdev.ecodes.KEY_V: ['v', 'V'],
        evdev.ecodes.KEY_B: ['b', 'B'],
        evdev.ecodes.KEY_N: ['n', 'N'],
        evdev.ecodes.KEY_M: ['m', 'M'],
        evdev.ecodes.KEY_COMMA: [',', '<'],
        evdev.ecodes.KEY_DOT: ['.', '>'],
        evdev.ecodes.KEY_SLASH: ['/', '?'],
        evdev.ecodes.KEY_SPACE: [' ', ' '],
        }
        self.ERROR_CHARACTER = '?'
        self.VALUE_UP = 0
        self.VALUE_DOWN = 1
        self.barcode_string_output = ''
        # for path in evdev.list_devices():
            # print('path:', path)
        self.dev = self.get_device()
        # print('selected device:', self.dev)
        try:
            self.dev.grab()
        except:
            self.dev.ungrab()
            time.sleep(3)
            self.dev.grab()
            logging.info(f"\n couldn't grab scanner")
            # print("couldn't grab scanner")
            pass

    def get_device(self):
        self.devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for self.device in self.devices:
            # print('device:', self.device)
            # print('info:', self.device.info)
            # print(self.device.path, self.device.name, self.device.phys)
            for vp in self.VENDOR_PRODUCT:
                if self.device.info.vendor == vp[0] and self.device.info.product == vp[1]:
                    return self.device
                else:
                    return None

    def barcode_reader_evdev(self):
        
        self.barcode_string_output = ''
        # barcode can have a 'shift' character; this switches the character set
        # from the lower to upper case variant for the next character only.
        self.shift_active = False
        for self.event in self.dev.read_loop():

            if self.event.code == evdev.ecodes.KEY_ENTER and self.event.value == self.VALUE_DOWN:
                #print('KEY_ENTER -> return')
                # all barcodes end with a carriage return
                return self.barcode_string_output
            elif self.event.code == evdev.ecodes.KEY_LEFTSHIFT or self.event.code == evdev.ecodes.KEY_RIGHTSHIFT:
                #print('SHIFT')
                self.shift_active = self.event.value == self.VALUE_DOWN
            elif self.event.value == self.VALUE_DOWN:
                ch = self.CHARMAP.get(self.event.code, self.ERROR_CHARACTER)[1 if self.shift_active else 0]
                #print('ch:', ch)
                # if the charcode isn't recognized, use ?
                self.barcode_string_output += ch
        
        return self.barcode_string_output
    
    def read_barcode(self):
        try:
            self.upcnumber = self.barcode_reader_evdev()
            # print(self.upcnumber)
        except KeyboardInterrupt:
            # print('Keyboard interrupt')
            pass
        except Exception as err:
            # print(err)
            pass
#        self.dev.ungrab()
        
        return self.upcnumber


class Counter:
    def __init__(self, arduino:Ardiuno, db:DB, camera=None, scanner=None) -> None:
        self.arduino = arduino
        self.stop_thread = False
        self.db = db
        self.old_local_ip = None
        self.old_err_msg = ""
        self.err_msg = ""
        self.old_c = 0 # analog input of watcher
        self.old_d = 0 # battery value

        signal.signal(signal.SIGINT, self.handler)
        if camera:
            self.camera = camera
        else:
            self.camera = None
        if scanner:
            self.scanner = scanner
        else:
            self.scanner = None
        self.watcher_live_signal = 60 * 5
        self.take_picture_interval = 60 * 5

    def handler(self, signal, frame):
        self.stop_thread = True
        return True

    def get_ip_address(self):
      try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # Google's public DNS server
        ip_address = s.getsockname()[0]  # Get the IP address
      except Exception as e:
        logging.info(f"\n ip address exception {e}")
        if not("-IP-address-" in self.err_msg):
            self.err_msg = self.err_msg + "-IP-address-" + str(e)
      finally:
        s.close()
      return ip_address

    def db_checker(self):
        while not self.stop_thread:
            try:
                data = self.db.read()
                if len(data):
                    if watcher_update(register_id=data[1], quantity=data[2], defect_quantity=data[3], send_img=len(data[4]) > 0, image_path=data[4], extra_info=json.loads(data[5]), timestamp=datetime.datetime.strptime(data[6], '%Y-%m-%d %H:%M:%S.%f')):
                        self.db.delete(data[0])
                time.sleep(1)
            except Exception as e:
                logging.info(f"\n db checker exception {e}")
                if not("db_checker" in self.err_msg):
                    self.err_msg = self.err_msg + "db_checker" + str(e)

    def run(self):
        self.last_server_signal = time.time()
        if self.camera:
            self.last_image = time.time()
        if self.scanner:
            self.old_barcode = ''
        
        
        while not self.stop_thread:
            try:
                data_saved = False
                send_image = False
                image_name = ""
                extra_info = {}
                ts = time.time()
                a ,b ,c, d ,dps = self.arduino.read_GPIO()
                if self.scanner:
                    barcode = self.scanner.read_barcode()
                # print(a, b, c, d , dps)
                if a + b > dps or ts - self.last_server_signal > self.watcher_live_signal:
                    logging.info(f"\n Captured the data")
                    self.last_server_signal = ts
                    if self.camera:
                        if ts - self.last_image > self.take_picture_interval:
                            captured, image_name = self.camera.capture_and_save()
                            # print(captured, image_name)
                            if captured:
                                send_image = True
                                self.last_image = ts
                            else:
                                send_image = False
                    if self.arduino.serial_connection:
                        extra_info = self.arduino.read_serial()
                    
                    if (c != self.old_c):
                        self.old_c  = c
                        extra_info.update({"analog" : self.old_c })

                    if (d != self.old_d):
                        self.old_d  = d
                        extra_info.update({"battery" : self.old_d })

                    self.local_ip = self.get_ip_address()
                    if (self.local_ip != self.old_local_ip ):
                        self.old_local_ip  = self.local_ip
                        extra_info.update({"local_ip" : self.old_local_ip })


                    if (self.err_msg != self.old_err_msg):
                        self.old_err_msg = self.err_msg
                        extra_info.update({"err_msg" : self.old_err_msg })


                    if self.scanner:
                        if barcode != '' and barcode != self.old_barcode:
                            self.old_barcode = barcode

                        if self.old_barcode != '':
                            extra_info.update({"batch_uuid" : str(self.old_barcode)})

                    timestamp = datetime.datetime.utcnow()

                    if watcher_update(hostname, quantity=a, defect_quantity=b, send_img=send_image, image_path=image_name, extra_info=extra_info, timestamp=timestamp):
                        data_saved = True
                    else:
                        try:
                            if self.db.write(register_id=hostname, a=a, b=b, extra_info=extra_info, timestamp=timestamp, image_name=image_name):
                                data_saved = True
                        except Exception as e:
                            logging.info(f"\n db_write {e}")
                            if not("db_write" in self.err_msg):
                                self.err_msg = self.err_msg + "db_write" + str(e)
                    if data_saved:
                        self.arduino.minus(a=a, b=b)

                time.sleep(1)
            except Exception as e:
                time.sleep(1)
                logging.info(f"\n counter run {e}")
                print(e)
                if not("counter_run" in self.err_msg):
                    self.err_msg = self.err_msg + "counter_run" + str(e)


db = DB()
arduino = Ardiuno()


if (arduino.gpio16_0.value and arduino.gpio18_0.value):
    camera = Camera()
    scanner = Scanner()
    counter = Counter(arduino=arduino, db=db, camera=camera)

elif arduino.gpio16_0.value:
    camera = Camera()
    counter = Counter(arduino=arduino, db=db, camera=camera)

elif arduino.gpio18_0.value:
    scanner = Scanner()
    counter = Counter(arduino=arduino, db=db, scanner=scanner)

else: 
    counter = Counter(arduino=arduino, db=db)

if  os.path.exists('/dev/ttyUSB0'):
    scanner1= Scanner('/dev/ttyUSB0')

Thread(target=counter.run).start()
time.sleep(10)
Thread(target=counter.db_checker).start()