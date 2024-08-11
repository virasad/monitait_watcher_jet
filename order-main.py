import requests
import json
from main_gpio import *

# Watcher hostname (register id)
register_id = '2024060901'

## URLs
header_url = 'https://develop-app.monitait.com/api/elastic-search/batch/'
stationID_url = f'https://develop-app.monitait.com/api/factory/watcher/{register_id}/'
sendbatch_url = 'https://develop-app.monitait.com/api/elastic-search/send-batch-report/'


## Setting the regiester ID in header
headers = {
    'Register-ID': register_id, 
    'Content-Type': 'application/json',
}

headers_resp = requests.get(header_url, headers=headers)

## Checking the headers resp
print("Headers ID resp: ",headers_resp.status_code)
order_list = headers_resp.json()
# Getting the station-id of watcher with watcher-reg-id
stationID_resp = requests.get(stationID_url, headers=headers)

print("Station ID resp: ", stationID_resp.status_code)  

# Sending batch report data (in the main while loop)
batches = [entry["_source"]["batch"] for entry in order_list]

## Waiting to scan sales_order value to find which batch should start
scaned_sales_order = 45

sales_order_batch = next(item for item in batches if item["sales_order"] == scaned_sales_order) # The order which the watcher should be consider
print(sales_order_batch)

arduino = main_gpio.Ardiuno()
camera = main_gpio.Camera()
db = main_gpio.DB()
scanner = main_gpio.Scanner()
counter = main_gpio.Counter(arduino=arduino, db=db, camera=camera, scanner=scanner)
Thread(target=counter.run).start()
time.sleep(10)
Thread(target=counter.db_checker).start()

## Reading the scanner value and send batch report
finishin_order_packing = False
# while not finishin_order_packing:
#       scan 