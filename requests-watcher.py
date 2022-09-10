import requests
import time
import logging
logging.basicConfig(filename='app.log', filemode='a', format='%(process)d - %(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.warning("proccess started")
if __name__ == "__main__":
    while True:
        try:
            r = requests.get("http://watcher-api.virasad.ir/30/30/1/1/1/1/1/1/1/1/1/1/1/1")
            if r.status_code != 201:
                logging.warning("abnormal status code: {}".format(r.status_code))
            time.sleep(10)
        except Exception as e:
            pass
            logging.error("exception!: {}".format(str(e)))
            time.sleep(10)
