import requests
import json


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
    
    
res = watcher_update("shyy2873gdj", 10)
print(res)

