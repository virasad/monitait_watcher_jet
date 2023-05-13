import json
import requests
import redis
import time

URL = 'http://thyestream.com' # not a real url obviously
watcher_register_key = '123457899'
r = redis.StrictRedis('localhost', 6379, charset="utf-8", decode_responses=True)
r.set("counter", "0")
def stream():
    r.incrby('counter', 1)
    print(r.get("counter"))
if __name__ == "__main__":
    while True:
        stream()
        time.sleep(1)
