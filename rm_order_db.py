import sqlite3
from utils.base_s import *

dbconnect = sqlite3.connect("/home/pi/monitait_watcher_jet/monitait.db", check_same_thread=False)

cursor2 = self.dbconnect.cursor()
if status == "total": 
      cursor2.execute('SELECT * FROM shipment_table')
      rows = cursor2.fetchall()
      if len(rows) == 0:
            cursor2.close()
      else:
            cursor2.close()

      cursor2.close()

print(rows, "Rows")

dbconnect.commit() # mv monitait.db monitait.db.old