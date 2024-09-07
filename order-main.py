from utils.base import *

register_id = str(socket.gethostname())
stationID = 0
scanned_sales_order = 0
## URLs
batch_url = 'https://develop-app.monitait.com/api/elastic-search/batch/'
stationID_url = f'https://develop-app.monitait.com/api/factory/watcher/{register_id}/'
sendbatch_url = 'https://develop-app.monitait.com/api/elastic-search/send-batch-report/'

try:
    os.system('./rm_py.sh')
except Exception as ex0:
    print(f"\n There are an error in openening the CPU version of watcher script, the error is {ex0}")  



class Counter:
    def __init__(self, arduino:Ardiuno, db:DB, camera:Camera, scanner:Scanner, batch_url: batch_url, stationID_url: stationID_url,
                 sendbatch_url: sendbatch_url, register_id: register_id, stationID: stationID, scanned_sales_order: scanned_sales_order) -> None:
        self.arduino = arduino
        self.stop_thread = False
        self.order_list = []
        self.db = db
        self.camera = camera
        self.scanner = scanner
        self.batch_url = batch_url
        self.stationID_url = stationID_url
        self.stationID = stationID
        self.sendbatch_url = sendbatch_url
        self.register_id = register_id
        self.scanned_sales_order = scanned_sales_order
        self.headers = {'Register-ID': self.register_id, 
                        'Content-Type': 'application/json'}
        self.watcher_live_signal = 60 * 5
        self.take_picture_interval = 60 * 5
        
    
    def db_order_checker(self):
        read_order_once = False
        db_checking_flag = False
        
        b_1 = 0
        while not self.stop_thread:
            if True:
                # Checking order list on the order DB to catch actual main quantity value
                if not read_order_once:
                    order_data = self.db.order_read()
                    main_order_dict = {}
                    if len(order_data) != 0:
                        read_order_once = True
                        db_checking_flag = True
                        print("db_order_checker order_data", order_data)
                        batches_json = json.loads(order_data[5]) # Convert batches json dumps to json
                        for batch in batches_json:
                            if batch['quantity'] != 0:
                                main_order_dict[batch['batch_uuid']]={
                                                                'quantity': batch['quantity'],
                                                                'assigned_id': batch['assigned_id']}
                            else:
                                pass
                    else:
                        db_checking_flag = False
                        read_order_once = False
                
                if db_checking_flag:
                    # Read the order to see is the quantity decreased
                    counted_order_data = self.db.order_read()
                    if len(counted_order_data) != 0:
                        counted_order_data_json = json.loads(counted_order_data[5])
                        for counted_batch in counted_order_data_json:
                            if counted_batch['quantity'] != 0:
                                main_quantity = main_order_dict[counted_batch['batch_uuid']]['quantity']
                                current_quantity = counted_batch['quantity']
                                if abs(main_quantity - current_quantity) >= 2:
                                    print(current_quantity, main_quantity, main_order_dict[counted_batch['batch_uuid']]['assigned_id'], self.scanned_sales_order)
                                    print("\n db_order_checker > start post requests")
                                    b_1 = b_1 + 2
                                    main_order_dict[counted_batch['batch_uuid']]['quantity'] = current_quantity
                                    # Post requests
                                    # Sendin batch to batch URL
                                    batch_report_body = {"batch_uuid":counted_batch['batch_uuid'], "assigned_id":counted_batch['assigned_id'],
                                                            "type": "new", "station": int(self.stationID),
                                                            "order_id": int(109),
                                                            "defected_qty": 0, "added_quantity": abs(main_quantity - current_quantity), 
                                                            "defect_image":[], "action_type": "stop"}  
                                    send_batch_response = requests.post(self.sendbatch_url, json=batch_report_body, headers=self.headers)

                                    print("db_order_checker > Send batch status code", send_batch_response.status_code)
                    else:
                        pass
                else:
                    pass
                time.sleep(1)
            # except Exception as e_orc:
            #     print(f"counter > db_order_checker {e_orc}")
    
    def run(self):
        self.last_server_signal = time.time()
        self.last_image = time.time()
        order_request_time_interval = 500 # Every "order_request_time_interval" secends, the order is requested from Monitait
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
        
        ## Main WHILE loop
        while not self.stop_thread:
            data_saved = False
            send_image = False
            or_barcode_scanned_flag = False # After scanning the operator OR barcode, this flag is set as True
            image_name = ""
            extra_info = {}
            order_batches = {}  
            
            # Getting order from batch API
            batch_reuest_s_t = time.time()
            while not or_barcode_scanned_flag:
                # Every the defined time interval, the watcher updates his order DB until OR is scanned
                if time.time() - batch_reuest_s_t > order_request_time_interval:
                    print("start to adding the data")
                    batch_reuest_s_t = time.time()
                    try:
                        batch_resp = requests.get(self.batch_url, headers=self.headers) 
                        # Added all batches to a list
                        order_list = batch_resp.json()  
                        orders = [entry["_source"]["batch"] for entry in order_list] 
                        
                        # Added the order batches to the order DB
                        for order in orders:
                            if order["sales_order"] == int(self.scanned_sales_order):
                            print("Getting to add order DB")
                            order_batches = order['batches']
                            # Save the orders to database
                            self.db.order_write(sales_order=order["sales_order"], product=order["product"], factory=order["factory"], 
                                                is_done = 0, batches_text= json.dumps(order_batches))
                    except Exception as ex1:
                        print(f"run > waiting to the OR barcode {ex1}")
                else:
                    pass
                
                # Reading the scanner to detect OR and start the counting process
                
            ## Checking the headers resp
            if orders != []:
                print("run > The order catched successfully", self.stationID)
                # Sending batch report data (in the main while loop)
                
                # Waiting to start by scanning "ORXXX" 
                order_counting_start_flag = False
                while not order_counting_start_flag:
                    # operator_scaning_barcode = self.scanner.read_barcode()
                    if "OR" in operator_scaning_barcode:
                        # separating OR scanned barcode
                        _, _, self.scanned_sales_order = operator_scaning_barcode.partition("OR")
                
                        order_counting_start_flag = True
                        print(f"run > The operator barcode scanned, the sales order is {self.scanned_sales_order}")
                        
                        
                    else:
                        pass
                # Starting to count the boxes
                finished_order_flag = False
                while (not finished_order_flag) and order_counting_start_flag:
                    
                    ts = time.time()
                    a ,b ,c, d ,dps = self.arduino.read_GPIO()
                    if abs(a - a_initial) >= 1:
                        print("\n\n run > a ,b ,c, d ,dps", a ,b ,c, d ,dps)
                        a_initial = a
                        box_scanned_barcode = 0
                        # Reading the box barcode
                        scanned_box_barcode_flag = False
                        assigned_id_flag = False
                        waiting_start_time = time.time()
                        #print("Order list before decreasing", json.dumps(order_batches))
                        while not scanned_box_barcode_flag:
                            # while True
                            box_scanned_barcode = Thread(target=scanner.read_barcode).start()
                            # box_scanned_barcode = self.scanner.read_barcode()
                            #rint("run > scanned barcoded of the box", box_scanned_barcode)
                            # Check if 10 seconds have passed
                            if abs(b - b_initial) < 1 or box_scanned_barcode != 0:
                                b_initial = b
                                print("run > inner loop")
                                for batch in order_batches:
                                    if batch['assigned_id']==str(box_scanned_barcode):
                                        assigned_id_flag = True
                                        # Extract batch_uuid
                                        batch_uuid = batch['batch_uuid']
                                        # Decrease quantity by 1 if it's greater than 0
                                        if batch['quantity'] > 0:
                                            batch['quantity'] -= 1
                                            
                                            print("Order list after decreasing", json.dumps(order_batches))
                                            
                                            # Update the order list
                                            self.db.order_update(sales_order=int(self.scanned_sales_order), product=order["product"], batches_text= json.dumps(order_batches), 
                                                                    factory=order["factory"], is_done = 0)
                                            
                                            print("run > The current assigned id quantity value (remainded value):", batch['quantity'])
                                        elif batch['quantity'] == 0:
                                            print("run > Counted value from this assined is has been finished")
                                            # The detected barcode is not on the order list
                                            self.arduino.gpio32_0.off()
                                            time.sleep(1)
                                            self.arduino.gpio32_0.on()
                                # Ejection process
                                if not assigned_id_flag:
                                    assigned_id_flag = False
                                    print("run > The barcode is not on the order list")
                                    # The detected barcode is not on the order list
                                    self.arduino.gpio32_0.off()
                                    time.sleep(1)
                                    self.arduino.gpio32_0.on()
                                    time.sleep(1)
                                scanned_box_barcode_flag = True
                                break
                            elif abs(b - b_initial) >= 1 and box_scanned_barcode == 0:
                                # The barcode can'not detect by the scanner 
                                b_initial = b
                                print("Box not detected by the scanner")
                                self.arduino.gpio32_0.off()
                                time.sleep(1)
                                self.arduino.gpio32_0.on()
                                time.sleep(1)
                                scanned_box_barcode_flag = True
                                break
                            elif time.time() - waiting_start_time > 50:
                                print("Time limitation has been exceeded")
                                scanned_box_barcode_flag = True
                                break
                            elif abs(b - b_initial) >= 1 and box_scanned_barcode != 0:
                                # The scanner works fine
                                pass
                        
                        if all(item['quantity'] == 0 for item in order_batches):
                            # Update the is_done column in the order list
                            self.db.order_update(sales_order=int(self.scanned_sales_order), is_done = 1)
                            finished_order_flag = True
                            break
                    # else:
                    #     print("Box not counted yet") 
                    
                    
                #     print(a, b , dps, barcode, self.old_barcode)
                #     if a + b > dps or ts - self.last_server_signal > self.watcher_live_signal:
                #         print("check")
                #         self.last_server_signal = ts
                #         if ts - self.last_image > self.take_picture_interval:
                #             captured, image_name = self.camera.capture_and_save()
                #             print(captured, image_name)
                #             if captured:
                #                 send_image = True
                #                 self.last_image = ts
                #             else:
                #                 send_image = False
                #         extra_info = self.arduino.read_serial()
                #         if barcode != '' and barcode != self.old_barcode:
                #             self.old_barcode = barcode

                #         if self.old_barcode != '':
                #             extra_info.update({"batch_uuid" : str(self.old_barcode)})

                #         timestamp = datetime.datetime.utcnow()
                #         if watcher_update(register_id, quantity=a, defect_quantity=b, send_img=send_image, image_path=image_name, extra_info=extra_info, timestamp=timestamp):
                #             data_saved = True
                #         else:
                #             if self.db.write(register_id=register_id, a=a, b=b, extra_info=extra_info, timestamp=timestamp, image_name=image_name):
                #                 data_saved = True
                #         if data_saved:
                #             self.arduino.minus(a=a, b=b)
                
            else:
                print("The orders list are empty, waiting to fill the order list")
                
            
            time.sleep(1)



arduino = Ardiuno()
camera = Camera()
db = DB()
scanner = Scanner()

counter = Counter(arduino=arduino, db=db, camera=camera, scanner=scanner, batch_url=batch_url, stationID_url= stationID_url,
                            sendbatch_url=sendbatch_url, register_id=register_id, stationID = stationID, 
                            scanned_sales_order=scanned_sales_order)
Thread(target=counter.run).start()
# time.sleep(10)
# Thread(target=counter.db_checker).start()
time.sleep(10)
Thread(target=counter.db_order_checker).start()
