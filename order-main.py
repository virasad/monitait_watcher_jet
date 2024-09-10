from utils.base import *

register_id = str(socket.gethostname())

## URLs
batch_url = 'https://app.monitait.com/api/elastic-search/batch/'
stationID_url = f'https://app.monitait.com/api/factory/watcher/{register_id}/'
sendbatch_url = 'https://app.monitait.com/api/elastic-search/send-batch-report/'

try:
    os.system('./rm_py.sh')
except Exception as ex0:
    print(f"\n There are an error in openening the CPU version of watcher script, the error is {ex0}")  



class Counter:
    def __init__(self, arduino:Ardiuno, db:DB, camera:Camera, scanner:Scanner, batch_url: batch_url, stationID_url: stationID_url,
                 sendbatch_url: sendbatch_url, register_id: register_id) -> None:
        self.arduino = arduino
        self.stop_thread = False
        self.order_list = []
        self.db = db
        self.camera = camera
        self.scanner = scanner
        self.batch_url = batch_url
        self.stationID_url = stationID_url
        self.sendbatch_url = sendbatch_url
        self.register_id = register_id
        self.headers = {'Register-ID': self.register_id, 
                        'Content-Type': 'application/json'}
        self.sales_order = 0
        self.scanned_box_barcode = 0
        self.stationID = 0
        self.order = ()
        self.order_product = 0
        self.order_factory = 0
        self.order_batches = ""
        self.db_order_checking_interval = 10 # Seconda
        self.watcher_live_signal = 60 * 5
        self.take_picture_interval = 60 * 5
        self.order_db_remove_interval = 12 * 3600  # Convert hours to seconds
    
    def db_order_checker(self):
        read_order_once = False
        db_checking_flag = False
        previus_sales_order = ""
        b_1 = 0
        st = time.time() 
        db_st = time.time()
        while not self.stop_thread:
            # Removing the order DB every specific time interval
            if time.time() - db_st > self.order_db_remove_interval:
                db_st = time.time()
                try:
                    # Removed all datafrom table
                    table_delete = self.db.order_delete(status="total")
                    # Getting update the watcher db
                    batch_resp = requests.get(self.batch_url, headers=self.headers) 
                    # Added all batches to a list
                    order_list = batch_resp.json()  
                    orders = [entry["_source"]["batch"] for entry in order_list] 
                    # Added the order batches to the order DB
                    for order in orders:
                        # Save the orders to database
                        self.db.order_write(sales_order=order["sales_order"], product=order["product"], factory=order["factory"], 
                                            is_done = 0, batches_text= json.dumps(order['batches']))
                except Exception as ex1:
                    print(f"db_order_checker > removing database {ex1}")
                
            # Checking order db every {self.db_order_checking_interval} second
            if time.time() - st > self.db_order_checking_interval and self.sales_order != 0:
                st = time.time() 
                try:
                    # Checking order list on the order DB to catch the quantity value
                    if self.sales_order != previus_sales_order:
                        main_order_dict = {}
                        # The sales order changed, so all data 
                        previus_sales_order = self.sales_order
                        main_salse_order_data = self.db.order_read(self.sales_order)
                        main_batches = json.loads(main_salse_order_data[5])
                        for batch in main_batches:
                            if batch['quantity'] != 0:
                                main_order_dict[batch['batch_uuid']]={
                                                                'quantity': batch['quantity'],
                                                                'assigned_id': batch['assigned_id']}
                            else:
                                pass
                    # Getting the scanned order list from order DB
                    print(f"DB function, the sales order is {self.sales_order} and the previus one is {previus_sales_order}")
                    
                    # Getting to detect in which batch changes is happend
                    updated_salse_order_data = self.db.order_read(self.sales_order)
                    updated_batches = json.loads(updated_salse_order_data[5])
                    for batches in updated_batches:
                        # Check if the order finished or not
                        is_done_value = updated_salse_order_data[4]
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
                                                        "order_id": int(self.sales_order),
                                                        "defected_qty": 0, "added_quantity": abs(main_quantity - current_quantity), 
                                                        "defect_image":[], "action_type": "stop"}  
                                send_batch_response = requests.post(self.sendbatch_url, json=batch_report_body, headers=self.headers)

                                print("db_order_checker > Send batch status code", send_batch_response.status_code)
                        else:
                            pass
                except Exception as ex2:
                    print(f"db_order_checker > checking the database {ex2}")

    
    def run(self):
        self.last_server_signal = time.time()
        self.last_image = time.time()
        order_request_time_interval = 5 # Every "order_request_time_interval" secends, the order is requested from Monitait
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
            
            # Getting order from batch API
            while not order_counting_start_flag:
                ##
                # The watcher updates his order DB until OR is scanned
                print("\n start to adding the data")
                try:
                    batch_resp = requests.get(self.batch_url, headers=self.headers) 
                    # Added all batches to a list
                    order_list = batch_resp.json()  
                    orders = [entry["_source"]["batch"] for entry in order_list] 
                    
                    # Added the order batches to the order DB
                    for order in orders:
                        print("sales_order", order["sales_order"], "quantity", order["quantity"])
                        # Save the orders to database
                        self.db.order_write(sales_order=order["sales_order"], product=order["product"], factory=order["factory"], 
                                            is_done = 0, batches_text= json.dumps(order['batches']))
                except Exception as ex1:
                    print(f"run > waiting to the OR barcode {ex1}")
                ##
                # Reading the scanner to detect OR and start the counting process
                try:
                    operator_scaning_barcode = self.scanner.read_barcode()
                    if "OR" in operator_scaning_barcode:
                        # separating OR scanned barcode
                        _, _, self.sales_order = operator_scaning_barcode.partition("OR")
                        
                        # Getting the scanned order list from order DB
                        self.order = self.db.order_read(self.sales_order)
                        print("Wait 5 seconds to start the counting")
                        # Checking is the scanned order in the order DB or not
                        if self.order != []:
                            order_counting_start_flag = True
                            # Getting batches, product, and factory from scanned order
                            self.order_batches = json.loads(self.order[5])
                            self.order_product = self.order[2]
                            self.order_factory = self.order[3]
                            print(f"The sales order {self.sales_order} is in the DB, the order is {self.order}")
                        else:
                            print(f"The sales order {self.sales_order} is not in the DB")
                    else:
                        pass
                except Exception as ex2:
                    print(f"run > reading scanner to detect OR {ex2}")
            ##
            # Start counting process
            while order_counting_start_flag:
                try:
                    # Reading the box entrance signal
                    ts = time.time()
                    a ,b ,c, d ,dps = self.arduino.read_GPIO()
                    # If a box entered 
                    if abs(a - a_initial) >= 1:
                        print("A box entered to the zone")
                        a_initial = a
                        box_in_order_batch = False
                        # Waiting to read the box barcode 
                        self.scanned_box_barcode = self.scanner.read_barcode()
                        if self.scanned_box_barcode != 0:
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
                                        self.db.order_update(sales_order=int(self.sales_order), product=self.order_product,
                                                            batches_text= json.dumps(self.order_batches), 
                                                            factory=self.order_factory, is_done = 0)
                                        print("run > The current assigned id quantity value (remainded value):", batch['quantity'])
                                    elif batch['quantity'] == 0:
                                        print("run > Counted value from this assined is has been finished")
                                        # Update the order list
                                        self.db.order_update(sales_order=int(self.sales_order), product=self.order_product,
                                                            batches_text= json.dumps(self.order_batches), 
                                                            factory=self.order_factory, is_done = 1)
                                        # The detected barcode is not on the order list
                                        self.arduino.gpio32_0.off()
                                        time.sleep(1)
                                        self.arduino.gpio32_0.on()
                                        time.sleep(1)
                            
                            # If the scanned barcode is not in the batches, eject it 
                            if not box_in_order_batch:
                                # The detected barcode is not on the order list
                                self.arduino.gpio32_0.off()
                                time.sleep(1)
                                self.arduino.gpio32_0.on()
                                time.sleep(1)
                    else:
                        pass
                except Exception as ex3:
                    print(f"run > reading scanner to detect OR {ex3}")
                # ##
                # # Send counted data to Monitait
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
                #     if barcode != '' and barcode != self.old_barcode:
                #         self.old_barcode = barcode

                #     if self.old_barcode != '':
                #         extra_info.update({"batch_uuid" : str(self.old_barcode)})

                #     timestamp = datetime.datetime.utcnow()
                #     if watcher_update(register_id, quantity=a, defect_quantity=b, send_img=send_image, image_path=image_name, extra_info=extra_info, timestamp=timestamp):
                #         data_saved = True
                #     else:
                #         if self.db.write(register_id=register_id, a=a, b=b, extra_info=extra_info, timestamp=timestamp, image_name=image_name):
                #             data_saved = True
                #     if data_saved:
                #         self.arduino.minus(a=a, b=b)
                # else:
                #     print("The orders list are empty, waiting to fill the order list")
                
            
            time.sleep(1)



arduino = Ardiuno()
camera = Camera()
db = DB()
scanner = Scanner()

counter = Counter(arduino=arduino, db=db, camera=camera, scanner=scanner, batch_url=batch_url,
                  stationID_url= stationID_url, sendbatch_url=sendbatch_url, register_id=register_id)

Thread(target=counter.run).start()
# time.sleep(10)
# Thread(target=counter.db_checker).start()
time.sleep(10)
Thread(target=counter.db_order_checker).start()
