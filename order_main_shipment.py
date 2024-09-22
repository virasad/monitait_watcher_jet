from utils.base_s import *
import glob

register_id = str(socket.gethostname())

## URLs slack
shipment_url = 'https://develop-app.monitait.com/api/factory/shipment-orders/'
stationID_url = f'https://develop-app.monitait.com/api/factory/watcher/{register_id}/'
sendshipment_url = 'https://develop-app.monitait.com/api/elastic-search/send-batch-report/'

try:
    os.system('./rm_py.sh')
except Exception as ex0:
    print(f"\n There are an error in openening the CPU version of watcher script, the error is {ex0}")  



class Counter:
    def __init__(self, arduino:Ardiuno, db:DB, camera:Camera, scanner, shipment_url: shipment_url, stationID_url: stationID_url,
                 sendshipment_url: sendshipment_url, register_id: register_id, usb_serial_flag) -> None:
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
        self.shipment_number = ""
        self.scanned_box_barcode = 0
        self.stationID = 0
        self.order = ()
        self.shipment_numbers = []
        self.order_product = 0
        self.order_factory = 0
        self.order_batches = ""
        self.is_done = 0
        self.db_order_checking_interval = 10 # Secends
        self.watcher_live_signal = 60 * 5
        self.take_picture_interval = 60 * 5
        self.order_db_remove_interval = 12 * 3600  # Convert hours to secends
    
    def db_order_checker(self):
        previus_shipment_number = ""
        b_1 = 0
        st = time.time() 
        db_st = time.time()
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
                    order_list = shipment_resp.json()  
                    orders = [entry["_source"]["batch"] for entry in order_list] 
                    # Added the order batches to the order DB
                    for order in orders:
                        # Save the orders to database
                        self.db.order_write(shipment_number=order["shipment_number"], product=order["product"], factory=order["factory"], 
                                            is_done = 0, batches_text= json.dumps(order['batches']))
                # except Exception as ex1:
                #     print(f"db_order_checker > removing database {ex1}")
                
            # Checking order db every {self.db_order_checking_interval} second
            if time.time() - st > self.db_order_checking_interval and self.shipment_number != 0:
                checking_order_db = False
                st = time.time() 
                if True:
                    # Checking order list on the order DB to catch the quantity value
                    if self.shipment_number != previus_shipment_number:
                        while not checking_order_db:
                            main_order_dict = {}
                            # The shaipment changed, so all data 
                            previus_shipment_number = self.shipment_number
                            main_shipment_number_data = self.db.order_read(self.shipment_number)
                            if main_shipment_number_data != []:
                                checking_order_db = True
                                print(f"DB, {previus_shipment_number}, main_shipment_number_data, {main_shipment_number_data}")
                                print("\n main_shipment_number_data", main_shipment_number_data)
                                main_batches = json.loads(main_shipment_number_data[5])
                                for batch in main_batches:
                                    if batch['quantity'] != 0:
                                        main_order_dict[batch['batch_uuid']]={
                                                                        'quantity': batch['quantity'],
                                                                        'assigned_id': batch['assigned_id']}
                                    else:
                                        pass
                            else: 
                                checking_order_db = False
                    # Getting the scanned order list from order DB
                    print(f"DB function, the shipment order is {self.shipment_number} and the previus one is {previus_shipment_number}")
                    
                    # Getting to detect in which batch changes is happend
                    updated_shipment_number_data = self.db.order_read(self.shipment_number)
                    updated_batches = json.loads(updated_shipment_number_data[5])
                    for batches in updated_batches:
                        # Check if the order finished or not
                        is_done_value = updated_shipment_number_data[4]
                        if is_done_value == 0:
                            main_quantity = main_order_dict[batches['batch_uuid']]['quantity']
                            current_quantity = batches['quantity']
                            if main_quantity != current_quantity:
                                # Update the quantity of the scanned box 
                                main_order_dict[batches['batch_uuid']]['quantity'] = current_quantity
                                
                                # Post requests
                                # Sending batch to batch URL
                                batch_report_body = {"batch_uuid":batches['batch_uuid'], "assigned_id":batches['assigned_id'],
                                                        "type": "new", "station": int(self.stationID),
                                                        "order_id": int(self.shipment_number),
                                                        "defected_qty": 0, "added_quantity": abs(main_quantity - current_quantity), 
                                                        "defect_image":[], "action_type": "stop"}  
                                send_shipment_response = requests.post(self.sendshipment_url, json=batch_report_body, headers=self.headers)

                                print("db_order_checker > Send batch status code", send_shipment_response.status_code)
                        else:
                            pass
                # except Exception as ex2:
                #     print(f"db_order_checker > checking the database {ex2}")

    
    def run(self):
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
                        for entry in results:
                            is_exist = self.db.order_write(shipment_number=entry["shipment_number"], 
                                                orders=json.dumps(entry['orders']), is_done=0)
                            if is_exist:
                                print(f"{entry['shipment_number']} is not exists")
                            else:
                                print(f"{entry['shipment_number']} is exists")
                            
                            # Added shipment number to the shipment list
                            if entry['shipment_number'] in self.shipment_numbers:
                                pass
                            else:
                                self.shipment_numbers.append(entry['shipment_number'])
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
                        shipment_scanned_barcode = str(shipment_scanned_barcode)
                    else:
                        shipment_scanned_barcode = shipment_scanned_barcode_byte_string
                    if shipment_scanned_barcode in self.shipment_numbers:
                        print(f"The scanned barcode is in the shipment number, {shipment_scanned_barcode}")
                        
                        # Getting the scanned order list from order DB
                        self.order = self.db.order_read(shipment_scanned_barcode)
                        print(f"\n oRDERS READ RESULTS {self.order}")
                        # Checking is the scanned order in the order DB or not
                        if self.order != []:
                            order_counting_start_flag = True
                            # Getting batches, product, and factory from scanned order
                            self.order_batches = json.loads(self.order[5])
                            self.order_product = self.order[2]
                            self.order_factory = self.order[3]
                            print("The batches", self.order_batches)
                        else:
                            order_counting_start_flag = False
                            print(f"The shipment order {self.shipment_number} is not in the DB, waiting to read valid data")
                        
                    else:
                        print()
                        print(f"There is no such shipment number, {shipment_scanned_barcode}, {type(shipment_scanned_barcode)}")

                # except Exception as ex2:
                #     print(f"run > reading scanner to detect OR {ex2}")
            ##
            # Start counting process
            while order_counting_start_flag:
                if True:
                    # Reading the box entrance signal
                    ts = time.time()
                    a ,b ,c, d ,dps = self.arduino.read_GPIO()
                    print(a ,b ,c, d ,dps)
                    # If the OK signal triggered
                    if abs(a - a_initial) >= 1:
                        print("Catched the OK signal")
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
                            if "OR" in self.scanned_box_barcode:
                                # The exit barcode scanned
                                print("The exit barcode scanned")
                                order_counting_start_flag = False
                            else:
                                # Checking is the scanned box barcode is in the order batches or not
                                for batch in self.order_batches:
                                    if batch['assigned_id']==str(self.scanned_box_barcode):
                                        # The box barcode is in the order
                                        box_in_order_batch = True
                                        # Getting to update the order DB
                                        batch_uuid = batch['batch_uuid']
                                        # Decrease quantity by 1 if it's greater than 0, else eject it
                                        if batch['quantity'] > 0:
                                            batch['quantity'] -= 1
                                            # Update the order list
                                            self.db.order_update(shipment_number=int(self.shipment_number), product=self.order_product,
                                                                batches_text= json.dumps(self.order_batches), 
                                                                factory=self.order_factory, is_done = 0)
                                            print("run > The current assigned id quantity value (remainded value):", batch['quantity'])
                                        elif batch['quantity'] == 0:
                                            # Remove the shipment number **
                                            print("run > Counted value from this assined is has been finished")
                                            # Update the order list
                                            self.db.order_update(shipment_number=int(self.shipment_number), product=self.order_product,
                                                                batches_text= json.dumps(self.order_batches), 
                                                                factory=self.order_factory, is_done = 1)
                                            # The detected barcode is not on the order list
                                            self.arduino.gpio32_0.off()
                                            time.sleep(1)
                                            self.arduino.gpio32_0.on()
                                            time.sleep(1)
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

counter = Counter(arduino=arduino, db=db, camera=camera, scanner=scanner, shipment_url=shipment_url,
                  stationID_url= stationID_url, sendshipment_url=sendshipment_url, register_id=register_id,
                  usb_serial_flag=usb_serial_flag)

Thread(target=counter.run).start()
# time.sleep(10)
# Thread(target=counter.db_checker).start()
# time.sleep(10)
# Thread(target=counter.db_order_checker).start()
