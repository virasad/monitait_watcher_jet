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
from utils import *

def get_flag():
    global my_flag
    return my_flag

def false_flag():
    global my_flag
    my_flag = False

def handler(signal, frame):
    global flag
    print('handler')
    flag = False



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
                # print(response.text)
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
                # print(response.text)
                return True
            except Exception as e:
                print(f"watcher update no image {e}")
                return False
    except Exception as e:
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
            pass
            print(f"DB > init {e}")


    def write(self, register_id=str(socket.gethostname()), a=0, b=0, extra_info={}, image_name="", timestamp=datetime.datetime.utcnow()):
        try:
            self.cursor.execute('''insert into monitait_table (register_id, temp_a, temp_b, image_name, extra_info, ts) values (?,?,?,?,?,?)''', (register_id, a, b, image_name, json.dumps(extra_info), timestamp))
            self.dbconnect.commit()
            print("db inserted")
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
        self.i = 0 # iterator for send a dummy 0 request
        self.j = 0
        self.k = 0
        self.restart_counter = 0
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
            self.serial_data = {}
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
                b = 0
                a = 0
                if in_bit_a and not(in_bit_b): # read arduino data a (OK)
                    a = 1*in_bit_0 + 2*in_bit_1 + 4*in_bit_2 + 8*in_bit_3
                    global my_flag
                    my_flag = True
                    print('image should be captured')
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
                #                    global my_flag
                #                    my_flag = True
                #                    print('image should be captured')
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
                time.sleep(0.01)
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
            self.frame = frame
            print(f'Frame shape: {frame.shape}')
            #self.frame = frame[self.roi[1]:self.roi[3], self.roi[0]:self.roi[2]]
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
                #success, frame = self.video_cap.read()
                
            #                 resized_frame = cv2.resize(frame, (1280, 720))
            #                 cv2.namedWindow(frame, cv2.WINDOW_NORMAL)
            #                 cv2.resizeWindow(frame, 640, 480)  
                            
                
                #                print(f"camera {success}")
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
        #         video_cap = cv2.VideoCapture(os.path.realpath(f"/dev/video{self.camera_id}"))
        video_cap = cv2.VideoCapture("rtsp://admin:1qaz!QAZ@192.168.1.124/cam/realmonitor?channel=1&subtype=1")
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

class Counter:
    def __init__(self, arduino:Ardiuno, db:DB, base_img_path: str, vcap1_url: str, area_thr: int) -> None:
        self.arduino = arduino
        self.stop_thread = False
        self.db = db
        self.watcher_live_signal = 60 * 5
        self.take_picture_interval = 60 * 5
        self.base_img = cv2.imread(base_img_path)
        self.vcap1 = cv2.VideoCapture(vcap1_url)
        self.area_thr = area_thr


    def db_checker(self):
        while not self.stop_thread:
            try:
                data = self.db.read()
                if len(data):
                    if watcher_update(register_id=data[1], quantity=data[2], defect_quantity=data[3], send_img=len(data[4]) > 0, image_path=f'/home/pi/monitait_watcher_jet/images/frame_{data[4]}_2.jpg', extra_info=json.loads(data[5]), timestamp=datetime.datetime.strptime(data[6], '%Y-%m-%d %H:%M:%S.%f')):
                        self.db.delete(data[0])
                time.sleep(1)
            except Exception as e:
                print(f"counter > db_checker {e}")

    def run(self):
        self.last_server_signal = time.time()
        self.last_image = time.time()
        start_time= time.time()
        frame_count = 0
        
        while not self.stop_thread:
            try:
                ret1, frame1 = self.vcap1.read()
                if get_flag():  # hook to capture images

                    false_flag()
                    images = []
                    frame_count += 1
                    cv2.imwrite(f'images/frame_{frame_count}.jpg', frame1)
                    # Print the current time before sleeping
                    if time.time() - start_time > 5:
                        s_t = time.time()
                        for i in range(45):
                            if time.time() - s_t > 1.5:
                                break
                            ret1, frame1_2 = self.vcap1.read()
                        
                        h, w = self.base_img.shape[:2]  # Get the height and width from base_img
                        cropped_img = frame1_2[0:h, 0:w].copy()  # Crop the image to match base_img dimensions
                        cv2.imwrite(f"results/cropped_img_{frame_count}.jpg",cropped_img)

                        if ret1:
                            cv2.imwrite(f'images/frame_{frame_count}_2.jpg', frame1_2)
                        adjusted_frame1 = adjust_lightness(cropped_img  , self.base_img)
                        subtracted_img = image_subtract(adjusted_frame1, self.base_img)
                        cv2.imwrite(f"results/subtracted_img_{frame_count}.jpg",subtracted_img)
                        box, area = find_largest_obj(subtracted_img)
                        quantity = 1
                        if area > self.area_thr:
                            quantity = 0
                            print(f"frame: {frame_count} STUCKED, area: {area}")
                        else:
                            print(f"frame: {frame_count} EMPTY, area: {area}")
                        hostname = str(socket.gethostname())
                        timestamp = datetime.datetime.utcnow()
                        data_saved = False
                        defect_quantity=(1-quantity)
                        timestamp = datetime.datetime.utcnow()
                        hostname = str(socket.gethostname())
                        extra_info = {"area": area, "frame": frame_count}
                        if watcher_update(hostname, quantity=quantity, defect_quantity=defect_quantity, send_img=True, extra_info=extra_info, image_path=f'/home/pi/monitait_watcher_jet/images/frame_{frame_count}_2.jpg', timestamp=timestamp):
                            data_saved = True
                        else:
                            if self.db.write(register_id=hostname, a=quantity, b=defect_quantity, extra_info=extra_info, timestamp=timestamp, image_name=f'{frame_count}'):
                                data_saved = True

                        if data_saved:
                            print("Data Saved Successfully!")
                        else:
                            print("Data failed to be saved!")
                    start_time = time.time()

                data_saved = False
                send_image = False
                a ,b ,c ,dps = self.arduino.read_GPIO()
                # print(f"counter > run {a} ,{b} ,{c} ,{dps}" )
                
                # time.sleep(1)
            except Exception as e:
                time.sleep(1)
                print(f"counter > run {e}")
my_flag = False
def main():
    time.sleep(4)
    print('dev_main started..')
    hostname = str(socket.gethostname())
    signal.signal(signal.SIGINT, handler)
    arduino = Ardiuno()
    # camera = Camera()
    db = DB()
    counter = Counter(arduino=arduino, 
                      db=db, 
                      base_img_path="/home/pi/monitait_watcher_jet/template.jpg", 
                      vcap1_url="rtsp://admin:1qaz!QAZ@192.168.1.124/cam/realmonitor?channel=1&subtype=1",
                      area_thr = 250)
    Thread(target=counter.run).start()
    time.sleep(1)
    Thread(target=counter.db_checker).start()

if __name__ == '__main__':
    main()
