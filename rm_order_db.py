import sqlite3
from utils.base_s import *

db = DB()

rows = db.shipment_read(status ="total")

print(rows, "Rows", len(rows))

# dbconnect.commit() # mv monitait.db monitait.db.old