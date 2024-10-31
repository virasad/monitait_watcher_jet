from utils.base_s import *
import glob
import sys
import time
import cv2, requests
import numpy as np
import json
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, 
                             QVBoxLayout, QWidget, QHeaderView, QLabel, QGroupBox, 
                             QFormLayout, QLineEdit)
from PyQt5.QtGui import QColor, QFont, QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtGui
from datetime import datetime, timezone

register_id = str(socket.gethostname())

## URLs 
shipment_url = 'https://app.monitait.com/api/factory/shipment-orders/?status=not_started'
stationID_url = f'https://app.monitait.com/api/factory/watcher/{register_id}/'
sendshipment_url = 'https://app.monitait.com/api/elastic-search/send-batch-report/'
live_stream_url = 'http://192.168.125.103:5000/video_feed/1'

url_dict = {"shipment_url": shipment_url, "stationID_url": stationID_url, 
            "sendshipment_url": sendshipment_url, "live_stream_url": live_stream_url}

## Redis 
redis_api = "192.168.125.103"
redis_port = 6379 
redis_db = 3

class MainWindow(QMainWindow):
    def __init__(self, arduino:Ardiuno, db:DB, camera:Camera, scanner, redis, dbcheck, url_dict: url_dict,  register_id: register_id, usb_serial_flag):
        super().__init__()
        
        # Create a QFont for bold text
        self.bold_font = QFont()
        self.bold_font.setBold(True)
        
        self.setWindowTitle("اطلاعات محموله")
        self.setGeometry(100, 100, 800, 600)
        
        # Create a QTableWidget for the title
        self.title_table = QTableWidget()  
        self.title_table.setRowCount(4)  
        self.title_table.setColumnCount(4)  
        
        self.item_row0_col0 = QTableWidgetItem("شماره محموله")  
        self.item_row0_col0.setBackground(QColor("lightGray"))  
        self.item_row0_col0.setFont(self.bold_font)
        self.title_table.setItem(0, 0, self.item_row0_col0)
        
        self.item_row0_col2 = QTableWidgetItem("نوع محموله")  
        self.item_row0_col2.setBackground(QColor("lightGray"))  
        self.item_row0_col2.setFont(self.bold_font)  
        self.title_table.setItem(0, 2, self.item_row0_col2)  
        
        self.item_row1_col0 = QTableWidgetItem("مقصد")  
        self.item_row1_col0.setFont(self.bold_font)    
        self.item_row1_col0.setBackground(QColor("lightGray")) 
        self.title_table.setItem(1, 0, self.item_row1_col0)  
        
        self.item_row1_col2 = QTableWidgetItem("مبدا")  
        self.item_row1_col2.setBackground(QColor("lightGray"))  
        self.item_row1_col2.setFont(self.bold_font)  
        self.title_table.setItem(1, 2, self.item_row1_col2)  
        
        self.item_row1_col3 = QTableWidgetItem("ساوه")  
        self.title_table.setItem(1, 3, self.item_row1_col3) 
        
        self.item_row2_col0 = QTableWidgetItem("شناسایی نشده")  
        self.item_row2_col0.setBackground(QColor("lightGray"))  
        self.item_row2_col0.setFont(self.bold_font)  
        self.title_table.setItem(2, 0, self.item_row2_col0)
        
        self.item_row2_col2 = QTableWidgetItem("عدم تطابق")  
        self.item_row2_col2.setBackground(QColor("lightGray"))  
        self.item_row2_col2.setFont(self.bold_font)  
        self.title_table.setItem(2, 2, self.item_row2_col2)
        
        
        self.item_row3_col0 = QTableWidgetItem("شمارش شده")  
        self.item_row3_col0.setBackground(QColor("lightGray"))  
        self.item_row3_col0.setFont(self.bold_font)  
        self.title_table.setItem(3, 0, self.item_row3_col0)
        
        self.item_row3_col2 = QTableWidgetItem("کالای درست")  
        self.item_row3_col2.setBackground(QColor("lightGray"))  
        self.item_row3_col2.setFont(self.bold_font)  
        self.title_table.setItem(3, 2, self.item_row3_col2) 
         
        # Set the column and rows width and height
        self.title_table.setColumnWidth(0, 200)  
        self.title_table.setColumnWidth(2, 200)  
        self.title_table.setColumnWidth(1, 500)  
        self.title_table.setColumnWidth(3, 500)  
        self.title_table.setColumnWidth(4, 500) 
        self.title_table.setRowHeight(0, 80)  
        self.title_table.setRowHeight(1, 80)  
        self.title_table.setRowHeight(2, 80)  
        self.title_table.setRowHeight(3, 80)  

        # Set layout direction to right-to-left
        self.title_table.setLayoutDirection(Qt.RightToLeft)

        # Make the header visible or set other properties as needed
        self.title_table.horizontalHeader().setVisible(False)  # Hide horizontal header if not needed
        self.title_table.verticalHeader().setVisible(False)  # Hide vertical header if not needed
        
    
        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(7)
        self.table_widget.setLayoutDirection(Qt.RightToLeft)
        self.table_widget.setHorizontalHeaderLabels([
            "کد کالا", "نام", " شمرده", "مانده", "کل", "واحد", "اجکت"])
        # self.table_widget.horizontalHeader().setVisible(False)  # Hide horizontal header if not needed
        self.table_widget.verticalHeader().setVisible(False)  # Hide horizontal header if not needed
        
        # Set the stylesheet for the table to increase text size
        self.table_widget.setStyleSheet("font-size: 40px;")  # Adjust size as needed

        # Make headers stretch to fill the window
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        self.table_widget.setGeometry(100, 50, 600, 400)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        # Create a layout to arrange the title and table
        layout = QVBoxLayout()
        
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        layout.setSpacing(0)  # Remove spacing between widgets

        layout.addWidget(self.title_table)  # Add title above the table
        layout.addWidget(self.table_widget)
        
        self.arduino = arduino
        self.db = db
        self.camera = camera
        self.scanner = scanner
        self.redis = redis
        self.dbcheck = dbcheck
        self.shipment_url = url_dict["shipment_url"]
        self.stationID_url = url_dict["stationID_url"]
        self.sendshipment_url = url_dict["sendshipment_url"]
        self.register_id = register_id
        self.usb_serial_flag = usb_serial_flag
        self.headers = {'Register-ID': f'{self.register_id}', 
                        'Content-Type': 'application/json'}
        self.scanned_value_old = b''
        self.shipment_number = b''
        self.shipment_type = None
        self.destination = None
        self.scanned_box_barcode = 0
        self.stationID = 0
        self.order_db = []
        self.shipment_numbers_list = []
        self.shipment_orders = None
        self.added_completed = 0
        self.completed = 0
        self.added_counted = 0
        self.counted = 0
        self.added_not_detected = 0
        self.not_detected = 0
        self.added_mismatch = 0
        self.mismatch = 0
        self.db_order_checking_interval = 1 
        self.order_db_remove_interval = 30 
        self.db_checking_flag = True
        self.updaing_table_from_url_flag = False
        self.stop_thread = False
        self.update_table_flag = False
        self.start_counting_flag = False
        self.barcode_flag = False
        self.is_done = 0
    
    def counting(self):
        self.last_server_signal = time.time()
        
        a ,b ,c, d ,dps = self.arduino.read_GPIO()
        a_initial = a
        b_initial = b
        
        # Getting the stationID from API 
        try:
            stationID_resp = requests.get(self.stationID_url, headers=self.headers)
            stationID_json = stationID_resp.json()
                                
            self.stationID = stationID_json['station']['id']
        except Exception as ex:
            print(f"headers except {ex}")
            
        ##
        ## Main WHILE loop
        while not self.stop_thread:
            order_counting_start_flag = False # To start counting process, this flag set as True when OR detected
            exit_flag = False
            # Getting order from batch API
            while not order_counting_start_flag:
                ##
                # Reading the scanner to detect OR and start the counting process
                if True:
                    if not exit_flag:
                        # shipment_scanned_barcode_byte_string  = self.scanner.read_barcode()
                        shipment_scanned_barcode_byte_string = self.scanned_value_old
                        # If the scanner output is serial, convert its output to str
                        if self.usb_serial_flag:    
                            shipment_scanned_barcode = shipment_scanned_barcode_byte_string.decode().strip()
                            self.shipment_number = str(shipment_scanned_barcode)
                        else:
                            self.shipment_number = shipment_scanned_barcode_byte_string
                    else:
                        exit_flag = False
                        self.shipment_number = self.scanned_value_old
                        print("****Exit barcode scanned.****", self.scanned_box_barcode, self.shipment_number)
                    
                    # Getting the scanned order list from order DB
                    self.order_db = self.db.shipment_read(self.shipment_number)
                    if self.order_db != []:
                        print("Shipment detected: ", self.shipment_number)
                        # Set zero the quantity counter value when a new shipment scanned
                        self.added_completed = 0
                        self.completed = 0
                        self.added_counted = 0
                        self.counted = 0
                        self.added_not_detected = 0
                        self.not_detected = 0
                        self.added_mismatch = 0
                        self.mismatch = 0
                        self.previous_quantities = {}
                        self.eject_box = {}
                        total_completed_quantity = 0
                        total_remained_quantity = 0 
                                              
                        # Defined to watcher not catched a additional signal
                        self.barcode_flag = False
                        self.updaing_table_from_url_flag = True
                        
                        # Update the scanner value to its initial state
                        self.scanned_value_old = b''
                        
                        self.arduino.gpio32_0.on()  # Turned off the ejector
                        
                        order_counting_start_flag = True
                        self.update_table_flag = True
                        # Getting batches, product, and factory from scanned order
                        self.shipment_orders = json.loads(self.order_db[4])

                        # Defined for shipment table
                        self.destination = self.order_db[2]
                        self.shipment_type = self.order_db[3]
                        json_data1 = json.loads(self.order_db[4])
                        json_data2 = json.loads(self.order_db[5])
                        
                        shipment_quantity_value = json.loads(self.order_db[11])
                        for order_id, item in shipment_quantity_value.items(): 
                            self.eject_box[order_id] = item[3]
                        
                        self.total_quantities = {item["id"]: item["quantity"] for item in json_data2}
                        
                        self.previous_quantities = {item["id"]: 0 for item in json_data1}
                        
                        # Read wrong and not detected values from db
                        self.completed = self.order_db[7]
                        self.counted = self.order_db[8]
                        self.mismatch = self.order_db[9]
                        self.not_detected = self.order_db[10]
                        self.orders_quantity_specification = json.loads(self.order_db[11])
                        
                        self.start_counting_flag = True
                    else:
                        self.start_counting_flag = False
                        order_counting_start_flag = False
                        # print(f"There is no such shipment number, {self.shipment_number}, {type(self.shipment_number)}")
                # except Exception as ex2:
                #     print(f"run > reading scanner to detect OR {ex2}")
            ##
            # Start counting process
            eject_ts = time.time()
            while order_counting_start_flag:
                if True:
                    if time.time() - eject_ts < 1:
                        self.arduino.gpio32_0.on()  # Turned off the ejector
                        
                    if self.scanned_box_barcode in self.shipment_numbers_list:
                        # The exit barcode scanned
                        print("The exit barcode scanned")
                        order_counting_start_flag = False
                        exit_flag = True
                        catching_signal = True
                        self.barcode_flag = False
                    
                    ts = time.time()
                    a ,b ,c, d ,dps = self.arduino.read_GPIO()
                    # If the OK signal triggered
                    if abs(a - a_initial) >= 1:
                        # print("\n ****Catched OK signal.****")
                        a_initial = a
                        a_initial_1 = a
                        self.added_counted += 1
                        self.counted += 1
                        
                        
                        # Going to catch second OK signal
                        catching_signal = False
                        time_out_flag = False
                        
                        # Waiting to read the box barcode 
                        s_time = time.time()
                        while not catching_signal:
                            a1 ,b1 ,c1, d1 ,dps1 = self.arduino.read_GPIO()
                            
                            if abs(a1 - a_initial_1) >= 1 or catching_signal or (time.time() - s_time > 5):
                                # print("Catched the second OK signal or barcode read, or time-out")
                                # Update the initial value
                                a_initial_1 = a1
                                catching_signal = True
                                time_out_flag = True
                            
                            if self.barcode_flag:
                                catching_signal = True
                                self.barcode_flag = False
                                
                                if self.redis == None:
                                    pass
                                else: 
                                    data = self.redis.rpop('dms')
                                    print(data, "data")
                                
                                # scanned_box_barcode_byte_string = self.scanner.read_barcode()
                                scanned_box_barcode_byte_string = self.scanned_value_old
                                if self.usb_serial_flag:    
                                    self.scanned_box_barcode = scanned_box_barcode_byte_string.decode().strip()
                                    self.scanned_box_barcode = str(self.scanned_box_barcode)
                                else:
                                    self.scanned_box_barcode = scanned_box_barcode_byte_string
                                print(self.scanned_box_barcode, "self.scanned_box_barcode")
                                box_in_order_batch = False
                                if self.scanned_box_barcode != '':
                                    
                                    # Checking if all barcode value is zeros or not
                                    if all(item['quantity'] == 0 for item in self.shipment_orders):
                                        print("All value of the quantity is zero")
                                        # Remove the shipment number **
                                        if self.shipment_number in self.shipment_numbers_list:
                                            self.shipment_numbers_list.remove(self.shipment_number)
                                        else:
                                            pass
                                        # Update the order list
                                        self.is_done = 1
                                        self.db.shipment_update(shipment_number=self.shipment_number, orders= json.dumps(self.shipment_orders), is_done = self.is_done)

                                    if self.scanned_box_barcode in self.shipment_numbers_list:
                                        # The exit barcode scanned
                                        print("The exit barcode scanned")
                                        order_counting_start_flag = False
                                        exit_flag = True
                                        catching_signal = True
                                        self.barcode_flag = False
                                    else:
                                        # Checking is the scanned box barcode is in the order batches or not
                                        for item in self.shipment_orders:
                                            # Updating total and remainded value                                    
                                            total_quantity = int(self.total_quantities[item["id"]])
                                            remainded_quantity = int(item['quantity'])
                                            # Checking is scanned value in the batches
                                            for batch in item['batches']:
                                                if batch['assigned_id']==str(self.scanned_box_barcode):
                                                    
                                                    # The box barcode is in the order
                                                    box_in_order_batch = True
                                                    # Decrease quantity by 1 if it's greater than 0, else eject it
                                                    if item['quantity'] > 0:
                                                        # print(f"Status:{self.scanned_box_barcode} is grabbed.")
                                                        # Decreasing the quantity in the shipments order and the batches list
                                                        item['quantity'] -= 1 
                                                        batch['quantity'] = str(int(batch['quantity']) - 1) 
                                                        remainded_quantity = item['quantity']
                                                        # Update the counted value
                                                        self.added_completed += 1
                                                        self.completed += 1
                                                        
                                                        # Calculate the counted value
                                                        counted_quantity = abs(total_quantity-item['quantity'])
                                                        # Update order table
                                                        self.is_done = 0
                                                                                                                
                                                        # Update the orders quantity specification dictionary and shipment table
                                                        utc_time = datetime.now(timezone.utc)
                                                        formatted_utc_time = utc_time.strftime("%Y-%m-%d %H:%M:%S")
                                                        self.orders_quantity_specification[item['product_number']] = [total_quantity, counted_quantity, remainded_quantity, self.eject_box[item['product_number']], item['product_name'], item['delivery_unit'], formatted_utc_time]
                                                        self.db.shipment_update(shipment_number=self.shipment_number, orders= json.dumps(self.shipment_orders), is_done = self.is_done, completed = self.completed,
                                                                                counted = self.counted, mismatch= self.mismatch, not_detected = self.not_detected, orders_quantity_specification = json.dumps(self.orders_quantity_specification))

                                                    elif item['quantity'] == 0:
                                                        # print(f"Status:{self.scanned_box_barcode} is finished.")
                                                        # Updatinging the quantity in the shipments order and the batches list
                                                        item['quantity'] = 0 
                                                        batch['quantity'] = 0 
                                                        
                                                        # Updating the quantity value
                                                        counted_quantity = total_quantity
                                                        remainded_quantity = 0
                                                        self.eject_box[item["product_number"]] += 1
                                                        # print(self.eject_box, "self.eject_box", item['product_number'])
                                                        
                                                        eject_ts = time.time()
                                                        # Update local order db
                                                        self.is_done = 0 
                                                        
                                                        # Update the orders quantity specification dictionary and the shipment table
                                                        utc_time = datetime.now(timezone.utc)
                                                        formatted_utc_time = utc_time.strftime("%Y-%m-%d %H:%M:%S")
                                                        
                                                        self.orders_quantity_specification[item['product_number']] = [total_quantity, counted_quantity, remainded_quantity, self.eject_box[item['product_number']], item['product_name'], item['delivery_unit'], formatted_utc_time]
                                                        
                                                        self.db.shipment_update(shipment_number=self.shipment_number, orders= json.dumps(self.shipment_orders), is_done = self.is_done, completed = self.completed,
                                                                                counted = self.counted, mismatch= self.mismatch, not_detected = self.not_detected, orders_quantity_specification = json.dumps(self.orders_quantity_specification))
                                                        
                                                        # The detected barcode is not on the order list
                                                        self.arduino.gpio32_0.off()
                            
                                        # If the scanned barcode is not in the batches, eject it 
                                        if not box_in_order_batch:
                                            # print(f"Status:{self.scanned_box_barcode} is not in the shipment.")
                                            self.added_mismatch += 1
                                            self.mismatch += 1
                                            eject_ts = time.time()
                                            # The detected barcode is not on the order list
                                            self.arduino.gpio32_0.off()
                                            # Update shipment table
                                            
                                            self.db.shipment_update(shipment_number=self.shipment_number, completed = self.completed, counted = self.counted, 
                                                                    mismatch= self.mismatch, not_detected = self.not_detected, 
                                                                    orders_quantity_specification = json.dumps(self.orders_quantity_specification))
                                else:
                                    # print("Status:the scanner could not catch the barcode.")
                                    self.added_not_detected += 1
                                    self.not_detected += 1
                                    eject_ts = time.time()
                                    # The detected barcode is not on the order list
                                    self.arduino.gpio32_0.off()
                                    # Update shipment table
                                    
                                    self.db.shipment_update(shipment_number=self.shipment_number, completed = self.completed, counted = self.counted, 
                                                                    mismatch= self.mismatch, not_detected = self.not_detected)
                                
                                # Update the old scanned value
                                self.scanned_value_old = b''
                        # If barcode could not catch a barcode value
                        if time_out_flag:
                            # Update the old scanned value
                            self.scanned_value_old = b''
                            # print("Status:time out.")
                            self.added_not_detected += 1
                            self.not_detected += 1
                            eject_ts = time.time()
                            # The detected barcode is not on the order list
                            self.arduino.gpio32_0.off()
                            # Update shipment table
                            self.db.shipment_update(shipment_number=self.shipment_number, completed = self.completed, counted = self.counted, 
                                                                    mismatch= self.mismatch, not_detected = self.not_detected)
                        
                        self.table_widget.setRowCount(0)  # Clear the table

    def scanner_read(self):
        while True:
            barcode_scanned_value = self.scanner.read_barcode()
            print(barcode_scanned_value, "barcode_scanned_value")
            if barcode_scanned_value != b'':
                self.scanned_value_old = barcode_scanned_value
                self.barcode_flag = True
                print("\n Scanned value is: ", self.scanned_value_old)


    def db_orders_updating(self):
        st_1 = time.time()
        
        order_request_time_interval = 2 # Every "order_request_time_interval" secends, the order update
        old_shipments_number = 0
        while not self.stop_thread:
            # The watcher updates his order DB until OR is scanned
            if True:
                if time.time() - st_1 > order_request_time_interval or self.db_checking_flag:
                    self.db_checking_flag = False
                    st_1 = time.time()
                    
                    shipments_number, shipment_numbers_list = self.dbcheck.db_checking(old_shipments_number, self.shipment_url, self.shipment_numbers_list, self.shipment_number, self.stationID)
                    old_shipments_number = shipments_number
                    self.shipment_numbers_list = shipment_numbers_list         
                else:
                    pass
            # except Exception as ex1:
            #     print(f"run > waiting to the OR barcode {ex1}")


    def db_checker(self):
        previus_shipment_number = ""
        extra_info = {}
        st = time.time() 
        db_st = time.time()
        shipment_db_checking_flag = False
        while not self.stop_thread:
            
            # Removing the finished shipment after sending its all order to the Monitait db
            if time.time() - db_st > self.order_db_remove_interval:
                db_st = time.time()
                if True:
                    # Find the completed orders from watcher local db
                    completed_orders_list = self.db.shipment_read(is_done=1)
                    if completed_orders_list == []:
                        pass
                    else:
                        print("Found a completed order list")
                        for item in completed_orders_list:
                            orders = json.loads(item[4])
                            orders_number = len(orders)
                            status_code_number = 0
                            for ord in orders:
                                ord_id = ord["id"]
                                current_quantity = int(ord['quantity'])
                                batch_uuid = ord['batches'][0]['batch_uuid']
                                assigned_id = ord['batches'][0]['assigned_id']
                                
                                batch_report_body = {"batch_uuid":batch_uuid, "assigned_id":assigned_id,
                                                                "type": "new", "station": int(self.stationID),
                                                                "order_id": int(ord_id),
                                                                "defected_qty": 0, "added_quantity": current_quantity, 
                                                                "defect_image":[], "action_type": "stop"}  

                                send_shipment_response = requests.post(self.sendshipment_url, json=batch_report_body, headers=self.headers)
                                if send_shipment_response.status_code == 200:
                                    status_code_number += 1
                                else:
                                    pass
                            if status_code_number==orders_number:
                                print(f"status code number {status_code_number}, order numbers {orders_number}")
                                self.db.shipment_delete(shipment_number=self.shipment_number, status="onetable")
                                
                                # Change the shopment number to prevent updating the local db
                                self.shipment_number = b''
                            else:
                                pass
                    
                # except Exception as ex1:
                #     print(f"db_orders_checker > removing database {ex1}")
                
            # Checking order db every {self.db_order_checking_interval} second
            if (time.time() - st > self.db_order_checking_interval) and (self.shipment_number != b'') and (not self.db_checking_flag):
                st = time.time() 
                if True:
                    
                    extra_info = {"shipment_number": self.shipment_number,  "added_counted": self.added_counted,
                                  "added_not_detected":self.added_not_detected, "added_mismatch": self.added_mismatch,
                                  "completed": self.completed, "counted": self.counted, 
                                  "not_detected": self.not_detected, "mismatch": self.mismatch}
                    r_c = watcher_update(
                            register_id=register_id,
                            quantity=self.added_completed,
                            defect_quantity=0,
                            send_img=False,
                            image_path=None,
                            product_id=0,
                            lot_info=0,
                            extra_info= extra_info)
                    
                    # Reset the added quantity parameters
                    self.added_completed = 0
                    self.added_counted = 0
                    self.added_not_detected = 0
                    self.added_mismatch = 0
                    
                    # Checking order list on the order DB to catch the quantity value
                    main_shipment_number_data = self.db.shipment_read(self.shipment_number)
                    if main_shipment_number_data and (self.shipment_number != previus_shipment_number):
                        print("updated the main dict")
                        main_shipment_orders_dict = {}
                        # The shaipment changed, so all data 
                        previus_shipment_number = self.shipment_number
                        shipment_db_checking_flag = True
                        main_shipment_orders = json.loads(main_shipment_number_data[4])
                        for item in main_shipment_orders:
                            order_id = item['id']
                            for batch in item['batches']:
                                if batch['quantity'] != 0:
                                    # Put all batches of a shipment orders to dictionary
                                    main_shipment_orders_dict[batch['batch_uuid']]={
                                                                    'quantity': int(batch['quantity']),
                                                                    'assigned_id': batch['assigned_id'],
                                                                    'order_id': order_id}
                                else:
                                    pass
                    
                    updated_shipment_number_data_ = self.db.shipment_read(self.shipment_number)
                    if shipment_db_checking_flag and updated_shipment_number_data_:
                        # Getting the scanned order list from order DB
                        # Getting to detect in which batch changes is happend
                        updated_shipment_number_data = json.loads(updated_shipment_number_data_[4])
                        for item in updated_shipment_number_data:
                            for batch in item['batches']:
                                # Check if the order finished or not
                                is_done_value = updated_shipment_number_data_[6]
                                current_quantity = int(batch['quantity'])
                                if (is_done_value == 0) and (current_quantity != 0):
                                    main_quantity = main_shipment_orders_dict[batch['batch_uuid']]['quantity']
                                    # If main quantity is not equal to current value update the table
                                    if main_quantity != current_quantity:
                                        # Update the quantity of the scanned box 
                                        main_shipment_orders_dict[batch['batch_uuid']]['quantity'] = current_quantity
                                        order_id_ = main_shipment_orders_dict[batch['batch_uuid']]['order_id']
                                        # Post requests
                                        # Sending batch to batch URL
                                        batch_report_body = {"batch_uuid":batch['batch_uuid'], "assigned_id":batch['assigned_id'],
                                                                "type": "new", "station": int(self.stationID),
                                                                "order_id": int(order_id_),
                                                                "defected_qty": 0, "added_quantity": abs(main_quantity - current_quantity), 
                                                                "defect_image":[], "action_type": "stop"}  
                                        send_shipment_response = requests.post(self.sendshipment_url, json=batch_report_body, headers=self.headers)
                                        print("****Send batch status code", send_shipment_response.status_code)
                                else:
                                    pass
                # except Exception as ex2:
                #     print(f"db_orders_checker > checking the database {ex2}")
    def update_table(self):
        previus_shipment_number = ""
        table_st = time.time()
        table_update_interval = 1
        table_updating_flag = True
        self.updaing_table_from_url_flag = True
        while not self.stop_thread:
            if True:
                # Checking order db every {table_update_interval} second
                if (time.time() - table_st > table_update_interval) and (self.order_db != []) and self.start_counting_flag:
                    table_st = time.time()
                    json_data1 = json.loads(self.order_db[4])
                    json_data2 = json.loads(self.order_db[5])
                    if self.update_table_flag:
                        self.update_table_flag = False
                        # Updating the table
                        # Create and set values 
                        self.item_row0_col1 = QTableWidgetItem(f"{self.shipment_number}")  
                        
                        self.item_row0_col3 = QTableWidgetItem(f"{self.shipment_type}")  
                        self.item_row1_col1 = QTableWidgetItem(f"{self.destination}")  
                        
                        self.item_row2_col1 = QTableWidgetItem(f"{0}")  
                        self.item_row2_col3 = QTableWidgetItem(f"{0}")  
                        
                        # Set the stylesheet for the table to increase text size
                        self.title_table.setStyleSheet("font-size: 25px;")  # Adjust size as needed
                    
                        # Set values for the rows and columns
                        self.title_table.setItem(0, 1, self.item_row0_col1)   
                        self.title_table.setItem(0, 3, self.item_row0_col3)   
                        self.title_table.setItem(1, 1, self.item_row1_col1)   
                        self.title_table.setItem(2, 1, self.item_row2_col1)   
                        self.title_table.setItem(2, 3, self.item_row2_col3) 
                        
                        # self.table_widget.setRowCount(0)  # Clear the table
                        for item in json_data1:
                            row_position = self.table_widget.rowCount()
                            self.table_widget.insertRow(row_position)

                            product_name = item["product_name"]

                            current_quantity = item["quantity"]
                            previous_quantity = self.previous_quantities[item["id"]]
                            total_quantity = self.total_quantities[item["id"]]
                            counted_quantity = abs(total_quantity-previous_quantity)
                            eject_value = self.eject_box[item["product_number"]]

                            # Add items to the table
                            self.table_widget.setItem(row_position, 0, QTableWidgetItem(str(item["product_number"])))
                            self.table_widget.setItem(row_position, 1, QTableWidgetItem(product_name))
                            self.table_widget.setItem(row_position, 2, QTableWidgetItem(str(counted_quantity)))
                            self.table_widget.setItem(row_position, 3, QTableWidgetItem(str(item["quantity"])))  # Set the quantity item
                            self.table_widget.setItem(row_position, 4, QTableWidgetItem(str(total_quantity)))
                            self.table_widget.setItem(row_position, 5, QTableWidgetItem(item["delivery_unit"]))
                            self.table_widget.setItem(row_position, 6, QTableWidgetItem(str(eject_value)))
                    
                    read_shipment_db = self.db.shipment_read(self.shipment_number)
                    if read_shipment_db != [] and self.start_counting_flag:
                        # self.table_widget.setRowCount(0)  # Clear the table
                        
                        completed_qt = read_shipment_db[7]
                        counted_qt = read_shipment_db[8]
                        mismatch_qt = read_shipment_db[9]
                        not_detected_qt= read_shipment_db[10]
                        json_data11 = json.loads(read_shipment_db[4])
                        json_data22 = json.loads(read_shipment_db[5])
                        
                        # self.item_row2_col1 = QTableWidgetItem(f"{not_detected_qt}")  
                        # self.item_row2_col3 = QTableWidgetItem(f"{mismatch_qt}")  
                        
                        self.title_table.setItem(2, 1, QTableWidgetItem(f"{not_detected_qt}")  )   
                        self.title_table.setItem(2, 3, QTableWidgetItem(f"{mismatch_qt}")) 
                        self.title_table.setItem(3, 1, QTableWidgetItem(f"{counted_qt}")) 
                        self.title_table.setItem(3, 3, QTableWidgetItem(f"{completed_qt}")) 
                        
                        orders_quantity_value = json.loads(read_shipment_db[6])
                        
                        orders_quantity_value_sorted = dict(sorted(orders_quantity_value.items(), key=lambda item: item[1][-1], reverse=True))
                        for order_id, item in orders_quantity_value_sorted.items(): 
                            total_qt = item[0]
                            counted_qt = item[1]
                            remainded_qt = item[2]
                            eject_qt = item[3]
                            product_name = item[4]
                            unit = item[5]
                            # Check if the row already exists
                            row_position = self.table_widget.rowCount()
                            existing_row = self.table_widget.findItems(str(order_id), Qt.MatchExactly)

                            if existing_row:
                                # If the order_id already exists, update the existing row
                                row_position = existing_row[0].row()
                            else:
                                # If it does not exist, insert a new row
                                self.table_widget.insertRow(row_position)
                            
                            # row_position = self.table_widget.rowCount()
                            # self.table_widget.insertRow(row_position)
                            self.table_widget.setItem(row_position, 0, QTableWidgetItem(str(order_id)))
                            self.table_widget.setItem(row_position, 1, QTableWidgetItem(str(product_name)))
                            self.table_widget.setItem(row_position, 2, QTableWidgetItem(str(counted_qt)))
                            self.table_widget.setItem(row_position, 3, QTableWidgetItem(str(remainded_qt)))  # Set the quantity item
                            self.table_widget.setItem(row_position, 4, QTableWidgetItem(str(total_qt)))
                            self.table_widget.setItem(row_position, 5, QTableWidgetItem(str(unit)))
                            self.table_widget.setItem(row_position, 6, QTableWidgetItem(str(eject_qt)))
                    
                        if self.updaing_table_from_url_flag:
                            self.updaing_table_from_url_flag = False
                            sel_orders_quantity_specification = {}
                            # Update the quantity by another calculation URL
                            extra_info_urls = f"https://app.monitait.com/api/elastic-search/watcher/?extra_info.shipment_number={self.shipment_number}"
                            extra_info_value = requests.get(extra_info_urls, headers=self.headers)
                            if extra_info_value.status_code == 200:
                                extra_info_json = extra_info_value.json()
                                if extra_info_json["result"]:
                                    print(extra_info_json["result"][-1]['_source']['watcher']['extra_info'], "200 rseponse")
                                    extra_info_dict = extra_info_json["result"][-1]['_source']['watcher']['extra_info']
                                    if 'completed' in extra_info_dict.keys():
                                        sel_completed = extra_info_dict['completed']
                                    else:
                                        sel_completed = 0
                                    
                                    if 'counted' in extra_info_dict.keys():
                                        sel_counted = extra_info_dict['counted']
                                    else:
                                        sel_counted = 0
                                        
                                    if 'mismatch' in extra_info_dict.keys():
                                        sel_mismatch = extra_info_dict['mismatch']
                                    else:
                                        sel_mismatch = 0
                                    
                                    if 'not_detected' in extra_info_dict.keys():
                                        sel_not_detected = extra_info_dict['not_detected']
                                    else:
                                        sel_not_detected = 0
                                else:
                                    sel_completed = 0
                                    sel_mismatch = 0
                                    sel_counted = 0
                                    sel_not_detected = 0
                            else:
                                sel_completed = 0
                                sel_mismatch = 0
                                sel_counted = 0
                                sel_not_detected = 0
                            
                            for ord in json_data11:
                                order_id = ord['id'] 
                                calculation_url = f"https://app.monitait.com/api/elastic-search/batch-report-calculations/?station_id={self.stationID}&order_id={order_id}"
                                order_remaind_value = requests.get(calculation_url, headers=self.headers)
                                if order_remaind_value.status_code == 200:
                                    order_remaind_value = order_remaind_value.json() 
                                    station_reports = order_remaind_value[0]['station_reports'][0]
                                    batch_quantity = int(station_reports['batch_quantity'])
                                    station_results = station_reports['result'][0] 
                                    total_completed_quantity = station_results['total_completed_quantity']
                                    total_remained_quantity = station_results['total_remained_quantity']
                                    # Update the order
                                    ord['batches'][0]['quantity'] = batch_quantity - total_completed_quantity
                                    ord['quantity'] = batch_quantity - total_completed_quantity
                                    
                                    # Updating remain column value from the unchanged order dictionary
                                    for item2 in json_data22:
                                        if item2['id'] == order_id:
                                            total_qt = item2['quantity']
                                else:
                                    # Updating remain column value from the unchanged order dictionary
                                    for item2 in json_data22:
                                        if item2['id'] == order_id:
                                            total_completed_quantity = 0
                                            total_remained_quantity = item2['quantity']
                                            total_qt = item2['quantity']

                                utc_time = datetime.now(timezone.utc)
                                formatted_utc_time = utc_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                                product_name = ord['product_name'] 
                                unit = ord['delivery_unit']
                                # total quantitiy, completed quantitiy, remainded quantitiy, eject quantitiy, name, unit
                                sel_orders_quantity_specification[ord['product_number']] = [total_qt, total_completed_quantity, total_remained_quantity, 0, product_name, unit, formatted_utc_time]
                            
                            # Upsert the shipment db
                            self.db.shipment_update(shipment_number = self.shipment_number, completed = sel_completed,
                                                    counted = sel_counted, mismatch = sel_mismatch,
                                                    not_detected = sel_not_detected, orders_quantity_specification = json.dumps(sel_orders_quantity_specification))
                            
            # except Exception as ex:
            #     print(f"table_update > exception {ex}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    arduino = Ardiuno()
    camera = Camera()
    db = DB()
    dbcheck = DbChecking(register_id=register_id, db = db)
    
    # try:
    #     redis_connection = redis.StrictRedis(redis_api, redis_port, db=redis_db)        
    #     response = redis_connection.ping()

    #     if response:
    #         print("Redis connection is successful!")
    #     else:
    #         redis_connection = None
    #         print("Redis connection failed.")
    # except redis.ConnectionError:
    #     redis_connection = None
    #     print("Could not connect to Redis.")
    
    redis_connection = None
    
    # Connected to the found scanner 
    # List all ttyUSB devices
    ttyUSB_devices = glob.glob('/dev/ttyUSB*')
    if ttyUSB_devices!= []:
        usb_serial_flag = True 
        scanner = UARTscanner(port=ttyUSB_devices[0], baudrate = 9600, timeout = 1)
    else:
        usb_serial_flag = False
        scanner = Scanner()
    
    counter = MainWindow(arduino=arduino, db=db, camera=camera, scanner=scanner, redis=redis_connection, dbcheck=dbcheck, url_dict=url_dict, register_id=register_id,
                    usb_serial_flag=usb_serial_flag)
    
    Thread(target=counter.scanner_read).start()
    Thread(target=counter.db_orders_updating).start()
    Thread(target=counter.db_checker).start()
    Thread(target=counter.update_table).start()
    Thread(target=counter.counting).start()
    counter.show()
    sys.exit(app.exec_())
