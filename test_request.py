import requests
import json
import time

def watcher_update(register_id, quantity):
    DATA = {
        "register_id" : register_id,
        "quantity" : quantity
    }
    HEADER = {
        "content-type": "application/json"
    }
    URL = "https://backend.monitait.com/api/factory/update-watcher/"
    r = requests.post(URL, data=json.dumps(DATA), headers=HEADER)
    return r.json()
    
while True:    
    try:
        res = watcher_update("1234567890", 0)
        print(res)
        time.sleep(60)
    except:
        pass
