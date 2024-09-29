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

register_id = str(socket.gethostname())

## URLs slack
shipment_url = 'https://develop-app.monitait.com/api/factory/shipment-orders/'
stationID_url = f'https://develop-app.monitait.com/api/factory/watcher/{register_id}/'
sendshipment_url = 'https://develop-app.monitait.com/api/elastic-search/send-batch-report/'


class MainWindow(QMainWindow):
    def __init__(self, arduino:Ardiuno, db:DB, camera:Camera, scanner, shipment_url: shipment_url, stationID_url: stationID_url,
                 sendshipment_url: sendshipment_url, register_id: register_id, usb_serial_flag):
        super().__init__()
        
        # Create a QFont for bold text
        self.bold_font = QFont()
        self.bold_font.setBold(True)
        
        self.setWindowTitle("اطلاعات محصول")
        self.setGeometry(100, 100, 800, 600)
        
        # Create a QTableWidget for the title
        self.title_table = QTableWidget()  # No need to specify rows and columns at this point
        self.title_table.setRowCount(2)  # Set 2 rows for 'a' and 'b'
        self.title_table.setColumnCount(4)  # Set 1 column for values
        
        self.item_row1_col1 = QTableWidgetItem("شماره محموله")  
        self.item_row1_col1.setBackground(QColor("gray"))  
        self.item_row1_col1.setFont(self.bold_font)
        self.title_table.setItem(0, 0, self.item_row1_col1)
        
        self.item_row1_col3 = QTableWidgetItem("نوع محموله")  
        self.item_row1_col3.setBackground(QColor("gray"))  
        self.item_row1_col3.setFont(self.bold_font)  
        self.title_table.setItem(0, 2, self.item_row1_col3)  
        
        self.item_row2_col1 = QTableWidgetItem("مقصد")  
        self.item_row2_col1.setFont(self.bold_font)    
        self.item_row2_col1.setBackground(QColor("gray")) 
        self.title_table.setItem(1, 0, self.item_row2_col1)  
        
        self.item_row2_col3 = QTableWidgetItem("مبدا")  
        self.item_row2_col3.setBackground(QColor("gray"))  
        self.item_row2_col3.setFont(self.bold_font)  
        self.item_row2_col4 = QTableWidgetItem("ساوه")  
        self.item_row2_col4.setFont(self.bold_font)  
         
        self.title_table.setItem(1, 2, self.item_row2_col3)   
        self.title_table.setItem(1, 3, self.item_row2_col4)  
        
        # Set the column and rows width and height
        self.title_table.setColumnWidth(0, 200)  
        self.title_table.setColumnWidth(2, 200)  
        self.title_table.setColumnWidth(1, 500)  
        self.title_table.setColumnWidth(3, 500)  
        self.title_table.setRowHeight(0, 100)  
        self.title_table.setRowHeight(1, 100)  

        # Set layout direction to right-to-left
        self.title_table.setLayoutDirection(Qt.RightToLeft)

        # Make the header visible or set other properties as needed
        self.title_table.horizontalHeader().setVisible(False)  # Hide horizontal header if not needed
        self.title_table.verticalHeader().setVisible(False)  # Hide vertical header if not needed
        
        
        # # Checking whether the live stream URL is alive or not
        # try:
        #     response = requests.head(live_stream_url, allow_redirects=True)
        #     if response.status_code == 200: 
        #         self.live_stream_flag = True
        #     else:
        #         self.live_stream_flag = False
        # except:
        #     self.live_stream_flag = True
        #     pass

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(6)
        self.table_widget.setLayoutDirection(Qt.RightToLeft)
        self.table_widget.setHorizontalHeaderLabels([
            "شماره", "نام", " شمرده", "مانده", "کل", "واحد"])
        # self.table_widget.horizontalHeader().setVisible(False)  # Hide horizontal header if not needed
        self.table_widget.verticalHeader().setVisible(False)  # Hide horizontal header if not needed
        
        # Set the stylesheet for the table to increase text size
        self.table_widget.setStyleSheet("font-size: 40px;")  # Adjust size as needed

        # Make headers stretch to fill the window
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Create a layout to arrange the title and table
        layout = QVBoxLayout()
        layout.addWidget(self.title_table)  # Add title above the table
        layout.addWidget(self.table_widget)
        
        # if self.live_stream_flag:
        #     # Create a QLabel for the image
        #     self.image_label = QLabel(self)
        #     layout.addWidget(self.image_label, alignment=Qt.AlignLeft | Qt.AlignTop)
        # else:
        #     pass
        
        # Create a container widget to hold the layout and image
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        
        self.arduino = arduino
        self.stop_thread = False
        self.order_list = []
        self.db = db
        self.camera = camera
        self.scanner = scanner
        self.shipment_url = shipment_url
        self.stationID_url = stationID_url
        self.sendshipment_url = sendshipment_url
        self.register_id = register_id
        self.usb_serial_flag = usb_serial_flag
        self.headers = {'Register-ID': self.register_id, 
                        'Content-Type': 'application/json'}
        self.shipment_number = None
        self.shipment_type = None
        self.destination = None
        self.scanned_box_barcode = 0
        self.stationID = 0
        self.shipment_db = []
        self.shipment_numbers_list = []
        self.shipment_orders = None
        self.is_done = 0
        self.db_order_checking_interval = 10 # Secends
        self.watcher_live_signal = 60 * 5
        self.take_picture_interval = 60 * 5
        self.order_db_remove_interval = 12 * 3600  # Convert hours to secends
    
    def update_table(self):

        # # Restart the timer
        # self.timer = threading.Timer(1.0, self.update_table)
        # self.timer.start()
        
        print("-----------------------")
        
        self.last_server_signal = time.time()
        self.last_image = time.time()
        db_checking_flag = True
        order_request_time_interval = 15 # Every "order_request_time_interval" secends, the order is requested from Monitait
        self.old_barcode = ''
        a_initial = 0
        b_initial = 0
        
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
            data_saved = False
            send_image = False
            order_counting_start_flag = False # To start counting process, this flag set as True when OR detected
            image_name = ""
            extra_info = {}
            st_1 = time.time()
            # Getting order from batch API
            while not order_counting_start_flag:
                ##
                # The watcher updates his order DB until OR is scanned
                if True:
                    if time.time() - st_1 > order_request_time_interval or db_checking_flag:
                        db_checking_flag = False
                        st_1 = time.time()
                        print("\n start to adding the data")
                        main_dict = requests.get(self.shipment_url, headers=self.headers) 
                        # Added all batches to a list
                        main_json = main_dict.json()  
                        results = main_json['results']
                        
                        # Added the order batches to the order DB
                        s3 = time.time()
                        for entry in results:
                            is_exist = self.db.order_write(shipment_number=entry["shipment_number"], 
                                                           destination=entry["destination"], 
                                                           shipment_type=entry["type"],
                                                           orders=json.dumps(entry['orders']), is_done=0)
                            if is_exist:
                                print(f"{entry['shipment_number']} is not exists")
                            else:
                                print(f"{entry['shipment_number']} is exists")
                            
                            # Added shipment number to the shipment list
                            if entry['shipment_number'] in self.shipment_numbers_list:
                                pass
                            else:
                                self.shipment_numbers_list.append(entry['shipment_number'])
                        print("\n Time of adding shipment to DB", time.time() - s3, "self.shipment_numbers_list", self.shipment_numbers_list)
                    else:
                        pass
                # except Exception as ex1:
                #     print(f"run > waiting to the OR barcode {ex1}")
                ##
                # Reading the scanner to detect OR and start the counting process
                if True:
                    shipment_scanned_barcode_byte_string  = self.scanner.read_barcode()
                    # If the scanner output is serial, convert its output to str
                    if self.usb_serial_flag:    
                        shipment_scanned_barcode = shipment_scanned_barcode_byte_string.decode().strip()
                        self.shipment_number = str(shipment_scanned_barcode)
                    else:
                        self.shipment_number = shipment_scanned_barcode_byte_string
                    if self.shipment_number in self.shipment_numbers_list :
                        # Getting the scanned order list from order DB
                        self.shipment_db = self.db.order_read(self.shipment_number)
                        self.destination = self.shipment_db[2]
                        self.shipment_type = self.shipment_db[3]
                        json_data1 = json.loads(self.shipment_db[4])
                        print("\n The orders", json_data1)
                        # Checking is the scanned order in the order DB or not
                        if self.shipment_db != []:
                            order_counting_start_flag = True
                            # Getting batches, product, and factory from scanned order
                            self.shipment_orders = json.loads(self.shipment_db[4])
                        else:
                            order_counting_start_flag = False
                            print(f"The order of shipment order {self.shipment_number} is empty")
                        # Updating the table
                        # Create and set values 
                        self.item_row1_col2 = QTableWidgetItem(f"{self.shipment_number}")  
                        self.item_row1_col2.setFont(self.bold_font)
                        
                        self.item_row1_col4 = QTableWidgetItem(f"{self.shipment_type}")  
                        self.item_row1_col4.setFont(self.bold_font)

                        self.item_row2_col2 = QTableWidgetItem(f"{self.destination}")  
                        self.item_row2_col2.setFont(self.bold_font)  
                        
                        # Set the stylesheet for the table to increase text size
                        self.title_table.setStyleSheet("font-size: 25px;")  # Adjust size as needed
                    
                        # Set values for the rows and columns
                        self.title_table.setItem(0, 1, self.item_row1_col2)   
                        self.title_table.setItem(0, 3, self.item_row1_col4)   
                        self.title_table.setItem(1, 1, self.item_row2_col2)   
                        
                        self.previous_quantities = {item["id"]: item["quantity"] for item in json_data1}
                        self.total_quantities = {item["id"]: item["quantity"] for item in json_data1}
                        
                        self.table_widget.setRowCount(0)  # Clear the table
                        for item in json_data1:
                            row_position = self.table_widget.rowCount()
                            self.table_widget.insertRow(row_position)

                            product_name = item["product_name"]

                            current_quantity = item["quantity"]
                            previous_quantity = self.previous_quantities[item["id"]]
                            total_quantity = self.total_quantities[item["id"]]
                            counted_quantity = abs(total_quantity-previous_quantity)

                            #  "شماره سفارش", "نام محصول", " شمارش شده", "مانده", "کل", "واحد تحویل"
                            # Add items to the table
                            self.table_widget.setItem(row_position, 0, QTableWidgetItem(str(item["id"])))
                            self.table_widget.setItem(row_position, 1, QTableWidgetItem(product_name))
                            self.table_widget.setItem(row_position, 2, QTableWidgetItem(str(counted_quantity)))
                            self.table_widget.setItem(row_position, 3, QTableWidgetItem(str(0)))  # Set the quantity item
                            self.table_widget.setItem(row_position, 4, QTableWidgetItem(str(total_quantity)))
                            self.table_widget.setItem(row_position, 5, QTableWidgetItem(item["delivery_unit"]))
                            
                            # self.table_widget.setRowCount(0)  # Clear the table
                    else:
                        print(f"There is no such shipment number, {self.shipment_number}, {type(self.shipment_number)}")

                # except Exception as ex2:
                #     print(f"run > reading scanner to detect OR {ex2}")
            ##
            # Start counting process
            test_flag = True
            while order_counting_start_flag:
                if True:
                    if test_flag:
                        print("In order counting while loop, waiting to the OK signal")
                        test_flag = False
                    # Reading the box entrance signal
                    ts = time.time()
                    a ,b ,c, d ,dps = self.arduino.read_GPIO()
                    # If the OK signal triggered
                    if abs(a - a_initial) >= 1:
                        print("\n ****Catched the OK signal****")
                        a_initial = a
                        # Waiting to read the box barcode 
                        scanned_box_barcode_byte_string = self.scanner.read_barcode()
                        if self.usb_serial_flag:    
                            self.scanned_box_barcode = scanned_box_barcode_byte_string.decode().strip()
                            self.scanned_box_barcode = str(self.scanned_box_barcode)
                        else:
                            self.scanned_box_barcode = scanned_box_barcode_byte_string
                        print("self.scanned_box_barcode", self.scanned_box_barcode)
                        box_in_order_batch = False
                        if self.scanned_box_barcode != 0:
                            if self.scanned_box_barcode in self.shipment_numbers_list:
                                # The exit barcode scanned
                                print("The exit barcode scanned")
                                order_counting_start_flag = False
                            else:
                                # Checking is the scanned box barcode is in the order batches or not
                                for item in self.shipment_orders:
                                    for batch in item['batches']:
                                        if batch['assigned_id']==str(self.scanned_box_barcode):
                                            # The box barcode is in the order
                                            box_in_order_batch = True
                                            # Decrease quantity by 1 if it's greater than 0, else eject it
                                            if item['quantity'] > 0:
                                                item['quantity'] -= 1 # Decreasing the quantity in the shipments order
                                                batch['quantity'] = str(int(batch['quantity']) - 1) # Decreasing the quantity in the batches list
                                                s = time.time()
                                                # Update the order list
                                                self.db.order_update(shipment_number=self.shipment_number,
                                                                    orders= json.dumps(self.shipment_orders),is_done = 0)
                                                print("Time of updating order db", time.time() - s)
                                                
                                                json_data2 = json.loads(self.shipment_orders[4])
                                                self.table_widget.setRowCount(0)  # Clear the table
                                                for item in json_data2:
                                                    row_position = self.table_widget.rowCount()
                                                    self.table_widget.insertRow(row_position)

                                                    remainded_quantity = int(batch['quantity']) - 1
                                                    
                                                    total_quantity = self.total_quantities[item["id"]]
                                                    counted_quantity = abs(total_quantity-remainded_quantity)

                                                    quantity_item = QTableWidgetItem(str(counted_quantity))
                                                    quantity_item.setBackground(QColor("red"))  # Highlight background in red
                                                    
                                                    # Add items to the table
                                                    # self.table_widget.setItem(row_position, 0, QTableWidgetItem(str(item["id"])))
                                                    # self.table_widget.setItem(row_position, 1, QTableWidgetItem(product_name))
                                                    self.table_widget.setItem(row_position, 2, quantity_item)
                                                    self.table_widget.setItem(row_position, 3, QTableWidgetItem(str(remainded_quantity)))  # Set the quantity item
                                                    # self.table_widget.setItem(row_position, 4, QTableWidgetItem(str(total_quantity)))
                                                    # self.table_widget.setItem(row_position, 5, QTableWidgetItem(item["delivery_unit"]))
                                                    
                                                    # self.table_widget.setRowCount(0)  # Clear the table
                                                
                                                print("run > The current assigned id quantity value (remainded value):", batch['quantity'])
                                            elif item['quantity']  == 0:
                                                print("run > Counted value from this assined is has been finished")
                                                # The detected barcode is not on the order list
                                                self.arduino.gpio32_0.off()
                                                time.sleep(1)
                                                self.arduino.gpio32_0.on()
                                                time.sleep(1)
                                            elif all(item['quantity'] == 0 for item in self.shipment_orders):
                                                print("run > All value of the quantity is zero")
                                                # Remove the shipment number **
                                                if self.shipment_number in self.shipment_numbers_list:
                                                    self.shipment_numbers_list.remove(self.shipment_number)
                                                else:
                                                    pass
                                                # The detected barcode is not on the order list
                                                self.arduino.gpio32_0.off()
                                                time.sleep(1)
                                                self.arduino.gpio32_0.on()
                                                time.sleep(1)
                                                # Update the order list
                                                self.db.order_update(shipment_number=self.shipment_number,
                                                                    orders= json.dumps(self.shipment_orders),is_done = 1)
                                # If the scanned barcode is not in the batches, eject it 
                                if not box_in_order_batch:
                                    print("The barcode is not on the list")
                                    # The detected barcode is not on the order list
                                    self.arduino.gpio32_0.off()
                                    time.sleep(1)
                                    self.arduino.gpio32_0.on()
                                    time.sleep(1)
                    # If the NG signal triggered
                    elif abs(b - b_initial) >= 1:
                        print("Recived NG signal")
                        b_initial = b
                        # Duo to reciving NG signal, the box should be ejected
                        self.arduino.gpio32_0.off()
                        time.sleep(1)
                        self.arduino.gpio32_0.on()
                        time.sleep(1)
                # except Exception as ex3:
                #     print(f"run > reading scanner to detect OR {ex3}")
                ##
                # Send counted data to Monitait
                # if a + b > dps or ts - self.last_server_signal > self.watcher_live_signal:
                #     print("check")
                #     self.last_server_signal = ts
                #     if ts - self.last_image > self.take_picture_interval:
                #         captured, image_name = self.camera.capture_and_save()
                #         print(captured, image_name)
                #         if captured:
                #             send_image = True
                #             self.last_image = ts
                #         else:
                #             send_image = False
                #     extra_info = self.arduino.read_serial()
                #     # if barcode != '' and barcode != self.old_barcode:
                #     #     self.old_barcode = barcode

                #     # if self.old_barcode != '':
                #     #     extra_info.update({"batch_uuid" : str(self.old_barcode)})

                #     timestamp = datetime.datetime.utcnow()
                #     if watcher_update(register_id, quantity=a, defect_quantity=b, send_img=send_image, image_path=image_name, extra_info=extra_info, timestamp=timestamp):
                #         data_saved = True
                #     else:
                #         if self.db.write(register_id=register_id, a=a, b=b, extra_info=extra_info, timestamp=timestamp, image_name=image_name):
                #             data_saved = True
                #     if data_saved:
                #         self.arduino.minus(a=a, b=b)
                # else:
                    # print("The orders list are empty, waiting to fill the order list")
            
            time.sleep(1)

            
    def db_order_checker(self):
        previus_shipment_number = ""
        b_1 = 0
        st = time.time() 
        db_st = time.time()
        shipment_db_checking_flag = False
        while not self.stop_thread:
            # Removing the order DB every 12 hours
            if time.time() - db_st > self.order_db_remove_interval:
                db_st = time.time()
                if True:
                    # Removed all datafrom table
                    table_delete = self.db.order_delete(status="total")
                    # Getting update the watcher db
                    shipment_resp = requests.get(self.shipment_url, headers=self.headers) 
                    # Added all batches to a list
                    main_json = main_dict.json()  
                    results = main_json['results']
                    # Added the order batches to the order DB
                    for entry in results:
                        # Save the orders to database
                        is_exist = self.db.order_write(shipment_number=entry["shipment_number"], orders=json.dumps(entry['orders']), is_done=0)
                # except Exception as ex1:
                #     print(f"db_order_checker > removing database {ex1}")
                
            # Checking order db every {self.db_order_checking_interval} second
            if time.time() - st > self.db_order_checking_interval and self.shipment_number != "":
                checking_order_db = False
                st = time.time() 
                if True:
                    # Checking order list on the order DB to catch the quantity value
                    if (self.shipment_number in self.shipment_numbers_list) and (self.shipment_number != previus_shipment_number):
                        while not checking_order_db:
                            main_shipment_orders_dict = {}
                            # The shaipment changed, so all data 
                            previus_shipment_number = self.shipment_number
                            main_shipment_number_data = self.db.order_read(self.shipment_number)
                            if main_shipment_number_data != []:
                                checking_order_db = True
                                shipment_db_checking_flag = True
                                print(f"DB, {previus_shipment_number}")
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
                            else: 
                                checking_order_db = False
                                shipment_db_checking_flag = False
                    
                    if shipment_db_checking_flag:
                        # Getting the scanned order list from order DB
                        # Getting to detect in which batch changes is happend
                        updated_shipment_number_data_ = self.db.order_read(self.shipment_number)
                        updated_shipment_number_data = json.loads(updated_shipment_number_data_[4])
                        for item in updated_shipment_number_data:
                            for batch in item['batches']:
                                # Check if the order finished or not
                                is_done_value = updated_shipment_number_data_[3]
                                if is_done_value == 0:
                                    main_quantity = main_shipment_orders_dict[batch['batch_uuid']]['quantity']
                                    current_quantity = int(batch['quantity'])
                                    if main_quantity != current_quantity:
                                        # Update the quantity of the scanned box 
                                        main_shipment_orders_dict[batch['batch_uuid']]['quantity'] = current_quantity
                                        order_id_ = main_shipment_orders_dict[batch['batch_uuid']]['order_id']
                                        print("order_id_", order_id_)
                                        # Post requests
                                        # Sending batch to batch URL
                                        batch_report_body = {"batch_uuid":batch['batch_uuid'], "assigned_id":batch['assigned_id'],
                                                                "type": "new", "station": int(self.stationID),
                                                                "order_id": int(order_id_),
                                                                "defected_qty": 0, "added_quantity": abs(main_quantity - current_quantity), 
                                                                "defect_image":[], "action_type": "stop"}  
                                        s2 = time.time()
                                        send_shipment_response = requests.post(self.sendshipment_url, json=batch_report_body, headers=self.headers)
                                        print("\n Send batch status code", send_shipment_response.status_code, "Post time", time.time()-s2)
                                else:
                                    pass
                # except Exception as ex2:
                #     print(f"db_order_checker > checking the database {ex2}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    arduino = Ardiuno()
    camera = Camera()
    db = DB()

    # Connected to the found scanner 
    # List all ttyUSB devices
    ttyUSB_devices = glob.glob('/dev/ttyUSB*')
    if ttyUSB_devices!= []:
        usb_serial_flag = True 
        print(f"The found UART ttyyUSB: {ttyUSB_devices}")
        scanner = UARTscanner(port=ttyUSB_devices[0], baudrate = 9600, timeout = 1)
    else:
        usb_serial_flag = False
        scanner = Scanner()

    counter = MainWindow(arduino=arduino, db=db, camera=camera, scanner=scanner, shipment_url=shipment_url,
                    stationID_url= stationID_url, sendshipment_url=sendshipment_url, register_id=register_id,
                    usb_serial_flag=usb_serial_flag)
    

    Thread(target=counter.update_table).start()
    time.sleep(0.1)
    Thread(target=counter.db_order_checker).start()
    time.sleep(0.1)
    counter.show()
    sys.exit(app.exec_())
