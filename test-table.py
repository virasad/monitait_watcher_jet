import sys
import time
import cv2, requests
import numpy as np
import json
import threading
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTableWidget, QTableWidgetItem, 
                             QVBoxLayout, QWidget, QHeaderView, QLabel, QGroupBox, 
                             QFormLayout, QLineEdit)
from PyQt5.QtGui import QColor, QFont, QPixmap, QImage
from PyQt5.QtCore import Qt, QTimer
from PyQt5 import QtGui
# Your initial data
data = (5, 'ZR2024092203', '[{"id": 163, "start_date": "2019-08-24T14:15:22Z", "delivery_date": "2019-08-24T14:15:22Z", "quantity": 3096, "delivery_unit": "CAR", "product_name": "\\u0645\\u0627\\u06cc \\u0628\\u06cc\\u0628\\u06bc", "product_number": "20240819", "default_ids": ["1234567891111"], "description": "TEST", "batches": [{"quantity": "3096", "batch_uuid": "a8715fb9-7b72-4d28-b0c3-7723f43b7f6d", "assigned_id": "1234567891111"}], "status": "not_started", "batch_status": "view"}, {"id": 164, "start_date": "2019-08-24T14:15:22Z", "delivery_date": "2019-08-24T14:15:22Z", "quantity": 3200, "delivery_unit": "CAR", "product_name": "\\u062f\\u0633\\u062a\\u0645\\u0627\\u0644 \\u0645\\u0631\\u0637\\u0648\\u0628", "product_number": "20240820", "default_ids": ["1234567892222"], "description": "TEST", "batches": [{"quantity": "3200", "batch_uuid": "bfc9d47a-ff2e-492e-9dd2-0eca1613dd68", "assigned_id": "1234567892222"}], "status": "not_started", "batch_status": "view"}, {"id": 165, "start_date": "2019-08-24T14:15:22Z", "delivery_date": "2019-08-24T14:15:22Z", "quantity": 3300, "delivery_unit": "CAR", "product_name": "\\u06a9\\u0644\\u06cc\\u0646 \\u0627\\u067e", "product_number": "20240821", "default_ids": ["1234567893333"], "description": "TEST", "batches": [{"quantity": "3300", "batch_uuid": "f0c24da2-afe9-4cfa-9a94-ab72168d025a", "assigned_id": "1234567893333"}], "status": "not_started", "batch_status": "view"}]', 0)
shipment_number = 'ZR2024092203'
shipment_type = "ZP50"
destination = "عجبشیر"
live_stream_url = "http://192.168.100.72:5000/video_feed/1"  # replace with your live stream URL

# Parse the JSON string into a Python list of dictionaries
json_data = json.loads(data[2])

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("اطلاعات محصول")
        self.setGeometry(100, 100, 800, 600)
        
        # Create a QFont for bold text
        bold_font = QFont()
        bold_font.setBold(True)

        # Create a QTableWidget for the title
        self.title_table = QTableWidget()  # No need to specify rows and columns at this point
        self.title_table.setRowCount(2)  # Set 2 rows for 'a' and 'b'
        self.title_table.setColumnCount(4)  # Set 1 column for values
        
        # Create and set values 
        item_row1_col1 = QTableWidgetItem("شماره محموله")  
        item_row1_col1.setBackground(QColor("gray"))  
        item_row1_col1.setFont(bold_font)
        item_row1_col2 = QTableWidgetItem(f"{shipment_number}")  
        item_row1_col2.setFont(bold_font)
        
        item_row1_col3 = QTableWidgetItem("نوع محموله")  
        item_row1_col3.setBackground(QColor("gray"))  
        item_row1_col3.setFont(bold_font)  
        item_row1_col4 = QTableWidgetItem(f"{shipment_type}")  
        item_row1_col4.setFont(bold_font)

        item_row2_col1 = QTableWidgetItem("مقصد")  
        item_row2_col1.setFont(bold_font)    
        item_row2_col1.setBackground(QColor("gray"))  
        item_row2_col2 = QTableWidgetItem(f"{destination}")  
        item_row2_col2.setFont(bold_font)  
        
        item_row2_col3 = QTableWidgetItem("مبدا")  
        item_row2_col3.setBackground(QColor("gray"))  
        item_row2_col3.setFont(bold_font)  
        item_row2_col4 = QTableWidgetItem("ساوه")  
        item_row2_col4.setFont(bold_font)  
                
        # Set the stylesheet for the table to increase text size
        self.title_table.setStyleSheet("font-size: 25px;")  # Adjust size as needed
    
        # Set values for the rows and columns
        self.title_table.setItem(0, 0, item_row1_col1)  
        self.title_table.setItem(0, 1, item_row1_col2)   
        self.title_table.setItem(0, 2, item_row1_col3)   
        self.title_table.setItem(0, 3, item_row1_col4)   
        self.title_table.setItem(1, 0, item_row2_col1)  
        self.title_table.setItem(1, 1, item_row2_col2)   
        self.title_table.setItem(1, 2, item_row2_col3)   
        self.title_table.setItem(1, 3, item_row2_col4)   
        
        # Set the column and rows width and height
        self.title_table.setColumnWidth(0, 200)  
        self.title_table.setColumnWidth(2, 200)  
        self.title_table.setColumnWidth(1, 500)  
        self.title_table.setColumnWidth(3, 500)  
        self.title_table.setRowHeight(0, 100)  
        self.title_table.setRowHeight(1, 100)  

        # Set layout direction to right-to-left
        self.title_table.setLayoutDirection(Qt.RightToLeft)

        # Make the header visible or set other properties as needed
        self.title_table.horizontalHeader().setVisible(False)  # Hide horizontal header if not needed
        self.title_table.verticalHeader().setVisible(False)  # Hide vertical header if not needed
        
        # # Checking whether the live stream URL is alive or not
        # try:
        #     response = requests.head(live_stream_url, allow_redirects=True)
        #     if response.status_code == 200: 
        #         self.live_stream_flag = True
        #     else:
        #         self.live_stream_flag = False
        # except:
        #     self.live_stream_flag = True
        #     pass

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(6)
        self.table_widget.setLayoutDirection(Qt.RightToLeft)
        self.table_widget.setHorizontalHeaderLabels([
            "شماره", "نام", " شمرده", "مانده", "کل", "تحویل"])
        # self.table_widget.horizontalHeader().setVisible(False)  # Hide horizontal header if not needed
        self.table_widget.verticalHeader().setVisible(False)  # Hide horizontal header if not needed
        
        # Set the stylesheet for the table to increase text size
        self.table_widget.setStyleSheet("font-size: 40px;")  # Adjust size as needed

        # Make headers stretch to fill the window
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Create a layout to arrange the title and table
        layout = QVBoxLayout()
        layout.addWidget(self.title_table)  # Add title above the table
        layout.addWidget(self.table_widget)
        
        # if self.live_stream_flag:
        #     # Create a QLabel for the image
        #     self.image_label = QLabel(self)
        #     layout.addWidget(self.image_label, alignment=Qt.AlignLeft | Qt.AlignTop)
        # else:
        #     pass
        
        # Create a container widget to hold the layout and image
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.previous_quantities = {item["id"]: item["quantity"] for item in json_data}
        self.total_quantities = {item["id"]: item["quantity"] for item in json_data}

        # Start the quantity decrease thread
        threading.Thread(target=self.decrease_quantity, daemon=True).start()

        # Start the timer to refresh the table
        self.timer = threading.Timer(1.0, self.update_table)
        self.timer.start()
    
    # def update_frame(self):
    #     ret, frame = self.cap.read()
    #     if ret:
    #         # Convert frame to RGB
    #         rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    #         # Get the dimensions of the frame
    #         h, w, ch = rgb_image.shape
    #         # # Create QImage from the RGB frame
    #         qimg = QImage(rgb_image.data, w, h, ch * w, QImage.Format_RGB888)
    #         # # Set the QImage on the QLabel
    #         self.image_label.setPixmap(QPixmap.fromImage(qimg))
        
    # def closeEvent(self, event):
    #     print(1)
    #     if self.live_stream_flag:
    #         self.cap.release()  # Release the video capture on close
    #         event.accept()
    #     else:
    #         pass
            

    def update_table(self):
        self.table_widget.setRowCount(0)  # Clear the table
        # if self.live_stream_flag:
        #     self.cap = cv2.VideoCapture(live_stream_url)  # Capture from the default camera
        #     self.update_frame()
        # else:
        #     pass
        
        for item in json_data:
            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)

            product_name = item["product_name"]

            current_quantity = item["quantity"]
            previous_quantity = self.previous_quantities[item["id"]]
            total_quantity = self.total_quantities[item["id"]]
            counted_quantity = abs(total_quantity-previous_quantity)

            # Check if the quantity has decreased
            quantity_item = QTableWidgetItem(str(current_quantity))
            if current_quantity < previous_quantity:
                quantity_item.setBackground(QColor("red"))  # Highlight background in red
            #  "شماره سفارش", "نام محصول", " شمارش شده", "مانده", "کل", "واحد تحویل"
            # Add items to the table
            self.table_widget.setItem(row_position, 0, QTableWidgetItem(str(item["id"])))
            self.table_widget.setItem(row_position, 1, QTableWidgetItem(product_name))
            self.table_widget.setItem(row_position, 2, QTableWidgetItem(str(counted_quantity)))
            self.table_widget.setItem(row_position, 3, quantity_item)  # Set the quantity item
            self.table_widget.setItem(row_position, 4, QTableWidgetItem(str(total_quantity)))
            self.table_widget.setItem(row_position, 5, QTableWidgetItem(item["delivery_unit"]))
            

        # Update previous quantities for the next iteration
        for item in json_data:
            self.previous_quantities[item["id"]] = item["quantity"]

        # Restart the timer
        self.timer = threading.Timer(1.0, self.update_table)
        self.timer.start()

    def decrease_quantity(self):
        while True:
            for item in json_data:
                if item["quantity"] > 0:
                    item["quantity"] -= 1  # Decrease the quantity by 100
            time.sleep(2)  # Wait for 1 second before the next decrease

# Main application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())