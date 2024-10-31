import requests
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
import redis
from datetime import datetime, timezone

register_id = str(socket.gethostname())

def handler(signal, frame):
    global flag
    print('handler')
    flag = False

signal.signal(signal.SIGINT, handler)

def watcher_update(register_id, quantity, defect_quantity, send_img, image_path="scene_image.jpg", product_id=0, lot_info=0, extra_info=None, timestamp=datetime.now(timezone.utc), *args, **kwargs):
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
                        os.remove(image_path)
                        return True
                    except Exception as e:
                        return True
                session.close
                return True
            except Exception as e:
                print(f"watcher update image {e}")
                return False
        else:
            try:
                response = requests.post(URL, data=json.dumps(DATA), headers={"content-type": "application/json"})
                return response.status_code
            except Exception as e:
                print(f"watcher update no image {e}")
                return False
    except Exception as e:
        session.close()
        return False

class DB:
    def __init__(self) -> None:
        if True:
            self.dbconnect = sqlite3.connect("/home/pi/monitait_watcher_jet/monitait.db", check_same_thread=False)
            cursor1 = self.dbconnect.cursor()
            cursor2 = self.dbconnect.cursor()
            cursor1.execute('''CREATE TABLE IF NOT EXISTS monitait_table (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, register_id TEXT, temp_a INTEGER NULL, temp_b INTEGER NULL, image_name TEXT NULL, extra_info JSON, ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL)''')
            cursor2.execute('''CREATE TABLE IF NOT EXISTS shipment_table (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, shipment_number TEXT NULL,
                            destination TEXT NULL, shipment_type TEXT NULL, orders TEXT NULL, unchanged_orders TEXT NULL, is_done INTEGER NULL, 
                            completed INTEGER NULL, counted INTEGER NULL, mismatch INTEGER NULL, not_detected INTEGER NULL, orders_quantity_specification TEXT NULL)''')
            
            # for column in columns:
            #     print(column)
            self.dbconnect.commit()
            cursor1.close()
            cursor2.close()
        # except Exception as e:
        #     print(f"DB > init {e}")
        #     pass

    def write(self, register_id=register_id, a=0, b=0, extra_info={}, image_name="", timestamp=datetime.now(timezone.utc)):
        try:
            cursor1 = self.dbconnect.cursor()
            cursor1.execute('''insert into monitait_table (register_id, temp_a, temp_b, image_name, extra_info, ts) values (?,?,?,?,?,?)''', (register_id, a, b, image_name, json.dumps(extra_info), timestamp))
            self.dbconnect.commit()
            cursor1.close()
            return True
        except Exception as e:
            print(f"DB > write {e}")
            cursor1.close()
            return False
    
    def shipment_write(self, shipment_number, destination, shipment_type, orders, unchanged_orders, is_done, completed, counted, mismatch, not_detected, orders_quantity_specification={}):
        if True:
            cursor2 = self.dbconnect.cursor()
            cursor2.execute('SELECT * FROM shipment_table WHERE shipment_number = ?', (shipment_number,))
            if cursor2.fetchone() is None:
                cursor2.execute('''insert into shipment_table (shipment_number, destination, shipment_type, orders, unchanged_orders, is_done, 
                                completed, counted, mismatch, not_detected, orders_quantity_specification) values (?,?,?,?,?,?,?,?,?,?,?)''',
                                (shipment_number, destination, shipment_type, orders, unchanged_orders, is_done, completed, counted, mismatch,
                                not_detected, orders_quantity_specification))
                self.dbconnect.commit()
                cursor2.close()
                return True
            else:
                cursor2.close()
                return False
        # except Exception as  e_ow:
        #     print(f"DB > order write {e_ow}")
        #     return False

    def read(self):
        try:
            cursor1 = self.dbconnect.cursor()
            cursor1.execute('SELECT * FROM monitait_table')
            rows = cursor1.fetchall()
            if len(rows) == 0:
                cursor1.close()
                return []
            else:
                cursor1.close()
                return rows[0]
        except Exception as e:
            print(f"DB > read {e}")
            return []
    
    def shipment_read(self, shipment_number=None, is_done=None, status="onetable"):
        if True:
            cursor2 = self.dbconnect.cursor()
            if status == "total": 
                cursor2.execute('SELECT * FROM shipment_table')
                rows = cursor2.fetchall()
                print("len", len(rows))
                if len(rows) == 0:
                    cursor2.close()
                    return []
                else:
                    cursor2.close()
                    return rows
                
                cursor2.close()
            elif status == "onetable":
                cursor2 = self.dbconnect.cursor()
                if shipment_number is not None:
                    cursor2.execute('SELECT * FROM shipment_table WHERE shipment_number = ?', (shipment_number,))
                    rows = cursor2.fetchall()
                    if len(rows) == 0:
                        cursor2.close()
                        return []
                    else:
                        cursor2.close()
                        return rows[0]
                                    
                if is_done is not None:
                    cursor2.execute('SELECT * FROM shipment_table WHERE is_done = ?', (is_done,))
                    rows = cursor2.fetchall()
                    if len(rows) == 0:
                        cursor2.close()
                        return []
                    else:
                        cursor2.close()
                        return rows
        # except Exception as e_or:
        #     print(f"DB > read order {e_or}")
        #     return []
        
    
    def delete(self, id):
        try:
            cursor1 = self.dbconnect.cursor()
            cursor1.execute("""DELETE from monitait_table where id = {}""".format(id))
            self.dbconnect.commit()
            cursor1.close()
            return True
        except Exception as e:
            print(f"DB > delete {e}")
            return False
    
    def shipment_delete(self, shipment_number=None, status="onetable"):
        if True:
            cursor2 = self.dbconnect.cursor()
            if status == "onetable":
                cursor2.execute("""DELETE from shipment_table where shipment_number = {}""".format(shipment_number))
            elif status == "total":
                cursor2.execute("""DELETE from shipment_table""")
            self.dbconnect.commit()
            cursor2.close()
            return True
        # except Exception as e_od:
        #     print(f"DB > delete order {e_od}")
        #     return False
        
    
    def shipment_upsert(self, shipment_number, destination, shipment_type, orders, unchanged_orders, is_done, completed, counted, mismatch, not_detected, orders_quantity_specification):
        try:
            cursor3 = self.dbconnect.cursor()
            cursor3.execute('''INSERT INTO shipment_table (shipment_number, destination, shipment_type, orders, unchanged_orders, is_done, completed, counted, mismatch, not_detected, 
                            orders_quantity_specification) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET
                            shipment_number = excluded.shipment_number, destination = excluded.destination,
                            shipment_type = excluded.shipment_type, orders = excluded.orders, unchanged_orders = excluded.unchanged_orders,
                            is_done = excluded.is_done, completed = excluded.completed, counted = excluded.counted,
                            mismatch = excluded.mismatch, not_detected = excluded.not_detected, 
                            orders_quantity_specification = excluded.orders_quantity_specification
                            ''', (shipment_number, destination, shipment_type, orders, unchanged_orders, is_done, completed, counted, mismatch, not_detected, orders_quantity_specification))
            self.dbconnect.commit()
        except Exception as e1:
            # Rollback in case of error
            print(f"An error occurred in shipment upsert: {e1}")
            cursor3.close()
    
    def shipment_update(self, shipment_number, destination=None, shipment_type=None, orders=None, unchanged_orders=None, is_done=None, 
                    completed=None, counted=None, mismatch=None, not_detected=None, orders_quantity_specification=None):
        if True:
            query = "UPDATE shipment_table SET "
            params = []
            # Check which column to updated
            if unchanged_orders is not None:
                query += "unchanged_orders = ?,"
                params.append(unchanged_orders)
            if orders is not None:
                query += "orders = ?, "
                params.append(orders)
            if destination is not None:
                query += "destination = ?, "
                params.append(destination)
            if shipment_type is not None:
                query += "shipment_type = ?, "
                params.append(shipment_type)
            if is_done is not None:
                query += "is_done = ?, "
                params.append(is_done)
            if completed is not None:
                query += "completed = ?, "
                params.append(completed)
            if counted is not None:
                query += "counted = ?, "
                params.append(counted)
            if mismatch is not None:
                query += "mismatch = ?, "
                params.append(mismatch)
            if not_detected is not None:
                query += "not_detected = ?, "
                params.append(not_detected)
            if orders_quantity_specification is not None:
                query += "orders_quantity_specification = ?, "
                params.append(orders_quantity_specification)
            # Remove the trailing comma and space
            query = query.rstrip(', ')
            
            # Add the WHERE clause
            query += " WHERE shipment_number = ?"
            params.append(shipment_number)

            # Execute the UPDATE statement
            self.dbconnect.execute(query, params)
            self.dbconnect.commit()
            return True
        # except Exception as e_ou:
        #     print(f"DB > update order {e_ou}")
        #     return False
        
        

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
        self.open_serial()
        Thread(target=self.run_GPIO).start()
        Thread(target=self.run_serial).start()

    def open_serial(self):
        try:
            self.ser = serial.Serial(
                    port='/dev/serial0', baudrate = 9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
            self.serial_connection = True
            self.serial_list = []
            self.buffer = b''
            self.last_received = ''
            self.ser.flushInput()
            self.extra_info = {}
            self.serial_data = {}
            return True
        except Exception as e:
            try:
                self.ser = serial.Serial(
                    port='/dev/serial1', baudrate = 9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
                self.serial_connection = True
                self.serial_list = []
                self.buffer = b''
                self.last_received = ''
                self.ser.flushInput()
                self.extra_info = {}
                self.serial_data = {}
                return True
            except Exception as ee:
                err_msg = err_msg + "-ser_init"
                self.serial_connection = False
                print(e)
                return False

    def close_serial(self):
        try:
            self.ser.close()
            return True
        except Exception as e:
            print(e)
            return False

    def int_to_bool_list(self, num):
        return [bool(num & (1<<n)) for n in range(4)]

    def set_gpio_value(self, x):
        b_list = self.int_to_bool_list(x)
        self.gpio33_2.value = b_list[2]
        self.gpio31_1.value = b_list[1]
        self.gpio29_0.value = b_list[0]
        
    def run_serial(self):
        while not self.stop_thread:
            try:
                tmp_serial_data = {}
                self.buffer += self.ser.read(2000)
                # self.ser.write("1\n".encode('utf-8'))
                # time.sleep(1)
                # self.ser.write("2\n".encode('utf-8'))
                # time.sleep(1)
                # self.ser.write("8\n".encode('utf-8'))
                time.sleep(0.01)
                if (b'\r\n' in self.buffer): # find line in serial data
                    last_received, self.buffer = self.buffer.split(b'\r\n')[-2:]
                    serial_list = str(last_received).split("'")[1].split(',')
                    for z in range(len(serial_list)):
                        tmp_serial_data.update({"d{}".format(z) : int(serial_list[z])})
                    self.serial_data = tmp_serial_data
                time.sleep(0.01)

            except Exception as e:
                if "Input/output" in str(e):
                    try:
                        self.close_serial()
                        self.open_serial()
                    except Exception as er:
                        print(er)
                if "fileno" in str(e):
                    try:
                        self.close_serial()
                        self.open_serial()
                    except Exception as ers:
                        print(ers)
                print(f"arduino Serial reader {e}")

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
                time.sleep(0.001)
            except Exception as e:
                print(f"arduino GPIO reader {e}")


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
            print([self.roi[1], self.roi[3], self.roi[0], self.roi[2]])
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
            date = datetime.now(timezone.utc)
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
        self.scanner_default_path = "/dev/input/event0"
        self.VENDOR_PRODUCT = [
        [0x0581, 0x011c], # [vendor, product]0581:011c
        [0x44176, 0x12290] # [vendor, product]
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
        for path in evdev.list_devices():
            print('path:', path)
        self.dev = self.get_device()
        print('selected device:', self.dev)
        try:
            self.dev.grab()
        except:
            self.dev.ungrab()
            time.sleep(3)
            self.dev.grab()
            pass

    def get_device(self):
        self.devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
        for self.device in self.devices:
            for vp in self.VENDOR_PRODUCT:
                print(vp)
                if self.device.info.vendor == vp[0] and self.device.info.product == vp[1]:
                    return self.device
                else:
                    return evdev.InputDevice(scanner_default_path)
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
        while True:
            try:
                self.upcnumber = self.barcode_reader_evdev()
                if self.upcnumber:  # If a barcode is read, return it
                    return self.upcnumber
            except KeyboardInterrupt:
                print('Keyboard interrupt')
                return None
            except Exception as err:
                print(err)
                return None
        
            return self.upcnumber

    # def run_with_timeout(self, timeout):
    #     thread = Thread(target=self.read_barcode)
    #     thread.start()
    #     thread.join(timeout)  # Wait for the thread to finish or timeout
    #     print("thread checker")
    #     if thread.is_alive():
    #         print("Task timed out!")
    #         return False
    #     else:
    #         print("Task finished within the timeout.")
    #         return True

class UARTscanner:
    def __init__(self, port, baudrate, timeout):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial = self.get_scanner()
        self.output = ""
    def get_scanner(self):
        try:
            self.ser = serial.Serial(port = self.port, baudrate = self.baudrate,
                                    bytesize=serial.EIGHTBITS, stopbits=serial.STOPBITS_ONE,
                                    parity = serial.PARITY_NONE, timeout = self.timeout)         
            return self.ser 
        except Exception as ex1:
            return None
            print(f"UARTscanner > get scanner {ex1}")
                
    def read_barcode(self):
        try:
            self.output = self.serial.readline()
            return self.output
        except Exception as ex2:
            print(f"UARTscanner > read data {ex2}")
            return None
           
        
class RedisConnection:
    def __init__(self, redis_hostname, redis_port):
        self.redis_hostname = redis_hostname
        self.redis_port = redis_port
        self.redis_connection = self.connect_to_redis()

    # Connecting to Radis database
    def connect_to_redis(self):
        return redis.Redis(self.redis_hostname, self.redis_port, db=3)

    def set_flag(self, list_lenght):
        with self.redis_connection.pipeline() as pipe:
            pipe.delete("camera_list")
            for i in range(list_lenght):
                pipe.rpush("camera_list", 0)
            pipe.execute()

    def update_encoder_redis(self, encoder):
        self.redis_connection.set("encoder_values", json.dumps(encoder))

    def set_captuting_flag(self, key):
        self.redis_connection.set(key, 1)

    def set_light_mode(self, mode):
        self.redis_connection.set("light_mode", mode)

    def update_dms_redis(self, dms):
        with self.redis_connection.pipeline() as pipe2:
            # pipe2.delete("dms")
            # for i in range(dms):
            pipe2.rpush("dms", dms)
            pipe2.execute()
        # self.redis_connection.set('dms', dms)

    def get_dms_redis(self):
        with self.redis_connection.pipeline() as pipe2:
            # pipe2.delete("dms")
            # for i in range(dms):
            dms_list = pipe2.rpop("dms")
            # pipe2.execute()
            if dms_list:
                return dms_list
            else:
                return []
        
        # self.redis_connection.set('dms', dms)


class DbChecking:
    def __init__(self, register_id, db):
        self.register_id = register_id
        self.headers = {'Register-ID': f'{self.register_id}', 
                        'Content-Type': 'application/json'}
        self.db = db
        
        
    def db_checking(self, init_shipments_number, db_api, shipments_list, scanned_shipment_number, stationID):
        db_api_response = requests.get(db_api, headers=self.headers) 
        if db_api_response.status_code == 200:
            # Added all batches to a list
            count_json = db_api_response.json()  
            # Checking how much page should be checks?
            shipments_number = count_json['count']
        else:
            shipments_number = 0
            print("DbChecking > could not connected to dp_api")
                
        if init_shipments_number != shipments_number and shipments_number != 0:
            
            # Finiding pagination number using shipment number
            if shipments_number > 10:
                if shipments_number % 10 == 0 :
                    pagination_number = shipments_number // 10
                else:
                    pagination_number = shipments_number // 10 + 1
            else:
                pagination_number = 1   
            
            if init_shipments_number < shipments_number:
                # Some shipments are added, so the new shipment should be added to the db 
                for index in range(pagination_number):
                    # Construct pagination url
                    page = index + 1
                    print(page, "pagination")
                    page_shipment_url = f'{db_api}&page={page}'
                    page_api_response = requests.get(page_shipment_url, headers=self.headers) 
                    
                    if page_api_response.status_code == 200:
                        # Added all shipment to a list
                        page_api_response_json = page_api_response.json()  
                        page_api_results = page_api_response_json['results']
                        
                        order_updating_flag = False
                        
                        # Added the order batches to the order DB
                        for entry in page_api_results:
                            # Added shipment number to the shipment list
                            if entry['shipment_number'] in shipments_list:
                                pass
                            else:
                                shipments_list.append(entry['shipment_number'])

                            if entry["shipment_number"] != scanned_shipment_number:
                                # Checking is the shipment on the local db or not
                                shipment_db_read = self.db.shipment_read(entry["shipment_number"]) 
                                if shipment_db_read == []:
                                    # Upsert the order db 
                                    unchanged_entry_order = entry['orders']
                                    
                                    # Upsert the shipment db 
                                    db_orders_quantity_dict = {}
                                    # Get additional value from extra infor url
                                    extra_info_urls = f"https://app.monitait.com/api/elastic-search/watcher/?extra_info.shipment_number={entry['shipment_number']}"
                                    extra_info_value = requests.get(extra_info_urls, headers=self.headers)
                                    if extra_info_value.status_code == 200:
                                        extra_info_json = extra_info_value.json()
                                        if extra_info_json["result"]:
                                            extra_info_dict = extra_info_json["result"][-1]['_source']['watcher']['extra_info']
                                            if 'completed' in extra_info_dict.keys():
                                                extra_info_completed = extra_info_dict['completed']
                                            else:
                                                extra_info_completed = 0
                                            
                                            if 'counted' in extra_info_dict.keys():
                                                extra_info_counted = extra_info_dict['counted']
                                            else:
                                                extra_info_counted = 0
                                                
                                            if 'mismatch' in extra_info_dict.keys():
                                                extra_info_mismatch = extra_info_dict['mismatch']
                                            else:
                                                extra_info_mismatch = 0
                                            
                                            if 'not_detected' in extra_info_dict.keys():
                                                extra_info_not_detected = extra_info_dict['not_detected']
                                            else:
                                                extra_info_not_detected = 0
                                        else:
                                            extra_info_completed = 0
                                            extra_info_counted = 0
                                            extra_info_mismatch = 0
                                            extra_info_not_detected = 0
                                    else:
                                        extra_info_completed = 0
                                        extra_info_counted = 0
                                        extra_info_mismatch = 0
                                        extra_info_not_detected = 0
                                    
                                    
                                    for ord in entry['orders']:
                                        order_id = ord['id'] 
                                        calculation_url = f"https://app.monitait.com/api/elastic-search/batch-report-calculations/?station_id={stationID}&order_id={order_id}"
                                        order_remaind_value = requests.get(calculation_url, headers=self.headers)
                                        if order_remaind_value.status_code == 200:
                                            order_updating_flag = True
                                            order_remaind_value = order_remaind_value.json() 
                                            
                                            station_reports = order_remaind_value[0]['station_reports'][0]
                                            batch_quantity = int(station_reports['batch_quantity'])
                                            
                                            station_results = station_reports['result'][0] 
                                            total_completed_quantity = station_results['total_completed_quantity']
                                            total_remained_quantity = station_results['total_remained_quantity']
                                            # Update the order
                                            ord['batches'][0]['quantity'] = batch_quantity - total_completed_quantity
                                            ord['quantity'] = batch_quantity - total_completed_quantity
                                            for item2 in unchanged_entry_order:
                                                if item2['id'] == order_id:
                                                    total_qt = item2['quantity']
                                        else:
                                            # Updating remain column value from the unchanged order dictionary
                                            for item2 in unchanged_entry_order:
                                                if item2['id'] == order_id:
                                                    total_completed_quantity = 0
                                                    total_remained_quantity = item2['quantity']
                                                    total_qt = item2['quantity']
                                        utc_time = datetime.now(timezone.utc)
                                        
                                        formatted_utc_time = utc_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                        product_name = ord['product_name'] 
                                        unit = ord['delivery_unit']
                                        # total quantitiy, completed quantitiy, remainded quantitiy, eject quantitiy, name, unit
                                        db_orders_quantity_dict[ord['product_number']] = [total_qt, total_completed_quantity, total_remained_quantity, 0, product_name, unit, formatted_utc_time]
                                    
                                    self.db.shipment_upsert(shipment_number=entry["shipment_number"], 
                                                        destination=entry["destination"], 
                                                        shipment_type=entry["type"],
                                                        orders=json.dumps(entry['orders']),
                                                        unchanged_orders=json.dumps(unchanged_entry_order),
                                                        is_done = 0, completed = extra_info_completed,
                                                        counted = extra_info_counted, mismatch = extra_info_mismatch,
                                                        not_detected = extra_info_not_detected, orders_quantity_specification = json.dumps(db_orders_quantity_dict))    
                            else:
                                # Shipment is equal to the scanned shipment
                                pass
                    else:
                        print("DbChecking > could not connected to page_dp_api")
            else:
                # Some shipments are removed, so the removed shipment should be added to the db
                print("Some shipments have been removed")
                # Reading all shipments and finding which one has been removed
                read_shipment_db = self.db.shipment_read(self.shipment_number)
                
            
                
            
        return shipments_number, shipments_list