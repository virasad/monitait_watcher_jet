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
from threading import Thread

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
                        return True
                    except Exception as e:
                        return True
                session.close
                return True
            except Exception as e:
                print(e)
                return False
        else:
            try:
                response = requests.post(URL, data=json.dumps(DATA), headers={"content-type": "application/json"})
                return True
            except Exception as e:
                print(e)
                return False
    except Exception as e:
        session.close()
        return False

class DB:
    def __init__(self) -> None:
        try:
            self.dbconnect = sqlite3.connect("/home/pi/monitait_watcher_jet/monitait.db")
            self.cursor = self.dbconnect.cursor()
            self.db_connection = True
            self.cursor.execute('''create table monitait_table (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, register_id TEXT, temp_a INTEGER NULL, temp_b INTEGER NULL, image_name TEXT NULL, extra_info JSON, ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL)''')
            self.dbconnect.commit()
        except Exception as e:
            print(f"DB > init {e}")


    def write(self, register_id=hostname, a=0, b=0, extra_info={}, image_name="", timestamp=datetime.datetime.utcnow()):
        try:
            self.cursor.execute('''insert into monitait_table (register_id, temp_a, temp_b, image_name, extra_info, ts) values (?,?,?,?,?,?)''', (register_id, a, b, image_name, json.dumps(extra_info), timestamp))
            self.dbconnect.commit()
            return True
        except Exception as e:
            print(f"DB > write {e}")
            return False

    def read(self):
        try:
            self.cursor.execute('SELECT * FROM monitait_table LIMIT 1')
            rows = self.cursor.fetchall()
            return rows[0]
        except Exception as e:
            print(f"DB > read {e}")
            return []

    def delete(self, id):
        try:
            self.cursor.execute("""DELETE from monitait_table where id = {}""".format(id))
            self.dbconnect.commit()
            return True
        except Exception as e:
            print(f"DB > delete {e}")
            return False

class Ardiuno:
    def __init__(self) -> None:
        self.stop_thread = False
        self.last_a = 0
        self.last_b = 0
        self.c = 0
        self.d = 0
        def handler(signal, frame):
            global flag
            print('handler')
            flag = False

        self.i = 0 # iterator for send a dummy 0 request
        self.j = 0
        self.k = 0
        self.restart_counter = 0
        signal.signal(signal.SIGINT, handler)
        self.gpio07_0 = GPIO(4, "in")
        self.gpio16_1 = GPIO(23, "in")
        self.gpio18_2 = GPIO(24, "in")
        self.gpio19_3 = GPIO(10, "in")
        self.gpio29_0 = GPIO(5, "out")
        self.gpio31_1 = GPIO(6, "out")
        self.gpio33_2 = GPIO(13, "out")
        self.gpio35_3 = GPIO(19, "out")
        self.gpio29_0.write(False)
        self.gpio31_1.write(False)
        self.gpio33_2.write(False)
        self.gpio35_3.write(False)
        self.gpio21_a = GPIO(9, "in")
        self.gpio23_b = GPIO(11, "in")
        self.gpio37_c = GPIO(26, "out")
        self.gpio26_d = GPIO(8, "out")
        self.gpio37_c.write(True) # identify default is a
        self.gpio26_d.write(True) # identify the default there is no read from RPI
        self.get_ts = 1
        self.buffer = b''
        self.open_serial()
        Thread(target=self.read_GPIO).start()
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
            self.serial_data = ""
            return True
        except Exception as e:
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
        self.gpio35_3.write(b_list[3])
        self.gpio33_2.write(b_list[2])
        self.gpio31_1.write(b_list[1])
        self.gpio29_0.write(b_list[0])

    def run_serial(self):
        while not self.stop_thread:
            try:
                tmp_seial_data = {}
                self.buffer += self.ser.read(2000)
                time.sleep(0.01)
                if (b'\r\n' in self.buffer): # find line in serial data
                    last_received, self.buffer = self.buffer.split(b'\r\n')[-2:]
                    serial_list = str(last_received).split("'")[1].split(',')
                    for z in range(len(serial_list)):
                        tmp_seial_data.update({"d{}".format(z) : int(serial_list[z])})
                    self.serial_data = tmp_seial_data
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
                in_bit_a = self.gpio21_a.read() # read arduino data
                in_bit_b = self.gpio23_b.read()
                in_bit_0 = self.gpio07_0.read()
                in_bit_1 = self.gpio16_1.read()
                in_bit_2 = self.gpio18_2.read()
                in_bit_3 = self.gpio19_3.read()

                if in_bit_a and not(in_bit_b): # read arduino data a (OK)
                    a = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
                if (a > 0):
                    self.set_gpio_value(a)
                    self.gpio26_d.write(False)
                    while (self.gpio21_a.read() != self.gpio23_b.read()):
                        time.sleep(0.001)
                    self.gpio26_d.write(True)
                    self.last_a += a
                    start_ts = time.time()
                    self.get_ts = 1/(start_ts - self.old_start_ts)+0.9*self.get_ts
                    self.old_start_ts = start_ts

                elif not(in_bit_a) and in_bit_b: # read arduino data b (NG)
                    b = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
                if (b > 0):
                    self.set_gpio_value(b)
                    self.gpio37_c.write(False) # identify it is b
                    self.gpio26_d.write(False)
                    while (self.gpio21_a.read() != self.gpio23_b.read()):
                        time.sleep(0.001)
                    self.gpio37_c.write(True) # identify default is a
                    self.gpio26_d.write(True)
                    self.last_b += b
                    start_ts = time.time()
                    self.get_ts = 1/(start_ts - self.old_start_ts)+0.9*self.get_ts
                    self.old_start_ts = start_ts
                elif in_bit_a and in_bit_b: # read arduino data d (A7 in 15 levels [0..15])
                    self.d = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
                else:                       # read arduino data c (A5 in 15 levels [0..15])
                    self.c = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
                time.sleep(0.001)
            except Exception as e:
                print(f"arduino GPIO reader {e}")


    def read_GPIO(self):
        return self.last_a, self.last_b, self.c, self.get_ts

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
            try:
                success, frame = self.video_cap.read()
                if success:
                    self.frame = frame[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
                    self.success = success
                else:
                    self.video_cap = self.camera_setup()
                    success, frame = self.video_cap.read()
                    self.frame = frame[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
                    self.success = success
                time.sleep(0.01)
            except:
                time.sleep(0.01)
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
        print('setuped')
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

class Counter:
    def __init__(self, arduino:Ardiuno, db:DB, camera:Camera) -> None:
        self.arduino = arduino
        self.stop_thread = False
        self.db = db
        self.camera = camera
        self.watcher_live_signal = 10
        self.take_picture_interval = 10

    def db_checker(self):
        while not self.stop_thread:
            try:
                data = self.db.read()
                if len(data):
                    if watcher_update(register_id=data[1], quantity=data[2], defect_quantity=data[3], send_img=len(data[4]) > 0, image_path=data[4], extra_info=json.loads(data[5]), timestamp=datetime.datetime.strptime(data[6], '%Y-%m-%d %H:%M:%S.%f')):
                        self.db.delete(data[0])
                time.sleep(1)
            except Exception as e:
                print(f"counter > db_checker {e}")

    def run(self):
        self.start_ts = time.time()
        while not self.stop_thread:
            try:
                data_saved = False
                send_image = False
                extra_info = {}
                ts = time.time()
                a ,b ,c ,dps = self.arduino.read_GPIO()
                print(f"counter > run {a} ,{b} ,{c} ,{dps}" )
                if a + b > dps or ts - self.start_ts > self.watcher_live_signal:
                    if ts - self.start_ts > self.take_picture_interval:
                        captured, image_name = self.camera.capture_and_save()
                        if captured:
                            send_image = True
                            self.take_picture_interval = ts
                        else:
                            send_image = False
                    extra_info = self.arduino.read_serial()
                    timestamp = datetime.datetime.utcnow()
                    if watcher_update(hostname, quantity=a, defect_quantity=b, send_img=send_image, image_path=image_name, extra_info=extra_info, timestamp=timestamp):
                        data_saved = True
                    else:
                        if self.db.write(register_id=hostname, a=a, b=b, extra_info=extra_info, timestamp=timestamp, image_name=image_name):
                            data_saved = True
                    if data_saved:
                        self.arduino.minus(a=a, b=b)
                time.sleep(1)
            except Exception as e:
                time.sleep(1)
                print(f"counter > run {e}")

arduino = Ardiuno()
camera = Camera()
db = DB()
counter = Counter(arduino=arduino, db=db, camera=camera)
Thread(target=counter.run).start()
time.sleep(10)
Thread(target=counter.db_checker).start()
