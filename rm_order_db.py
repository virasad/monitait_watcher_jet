import sqlite3

dbconnect = sqlite3.connect("/home/pi/monitait_watcher_jet/monitait.db", check_same_thread=False)
cursor = dbconnect.cursor()



cursor.execute("""DELETE from watcher_order_table""")
dbconnect.commit() # mv monitait.db monitait.db.old