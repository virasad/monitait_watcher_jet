import sys
import time
import json
import threading
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QHeaderView, QLabel
from PyQt5.QtGui import QColor, QFont, QPixmap
from PyQt5.QtCore import Qt

# Your initial data
data = (5, 'ZR2024092203', '[{"id": 163, "start_date": "2019-08-24T14:15:22Z", "delivery_date": "2019-08-24T14:15:22Z", "quantity": 3096, "delivery_unit": "CAR", "product_name": "\\u0645\\u0627\\u06cc \\u0628\\u06cc\\u0628\\u06bc", "product_number": "20240819", "default_ids": ["1234567891111"], "description": "TEST", "batches": [{"quantity": "3096", "batch_uuid": "a8715fb9-7b72-4d28-b0c3-7723f43b7f6d", "assigned_id": "1234567891111"}], "status": "not_started", "batch_status": "view"}, {"id": 164, "start_date": "2019-08-24T14:15:22Z", "delivery_date": "2019-08-24T14:15:22Z", "quantity": 3200, "delivery_unit": "CAR", "product_name": "\\u062f\\u0633\\u062a\\u0645\\u0627\\u0644 \\u0645\\u0631\\u0637\\u0648\\u0628", "product_number": "20240820", "default_ids": ["1234567892222"], "description": "TEST", "batches": [{"quantity": "3200", "batch_uuid": "bfc9d47a-ff2e-492e-9dd2-0eca1613dd68", "assigned_id": "1234567892222"}], "status": "not_started", "batch_status": "view"}, {"id": 165, "start_date": "2019-08-24T14:15:22Z", "delivery_date": "2019-08-24T14:15:22Z", "quantity": 3300, "delivery_unit": "CAR", "product_name": "\\u06a9\\u0644\\u06cc\\u0646 \\u0627\\u067e", "product_number": "20240821", "default_ids": ["1234567893333"], "description": "TEST", "batches": [{"quantity": "3300", "batch_uuid": "f0c24da2-afe9-4cfa-9a94-ab72168d025a", "assigned_id": "1234567893333"}], "status": "not_started", "batch_status": "view"}]', 0)
shipment_number = 'ZR2024092203'
# Parse the JSON string into a Python list of dictionaries
json_data = json.loads(data[2])

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("اطلاعات محصول")
        self.setGeometry(100, 100, 800, 600)

        # Create a QLabel for the title
        title_label = QLabel(f"جدول اطلاعات محصول، شماره محموله {shipment_number} ")
        title_label.setFont(QFont("Arial", 20))  # Set font and size
        title_label.setStyleSheet("font-weight: bold; color: blue;")  # Style the title

        self.table_widget = QTableWidget()
        self.table_widget.setColumnCount(7)
        self.table_widget.setLayoutDirection(Qt.RightToLeft)
        self.table_widget.setHorizontalHeaderLabels([
            "آی دی", "نام محصول", "شماره محصول", "تعداد", 
            "واحد تحویل", "تاریخ شروع", "تاریخ تحویل"])

        # Set the stylesheet for the table to increase text size
        self.table_widget.setStyleSheet("font-size: 25px;")  # Adjust size as needed

        # Make headers stretch to fill the window
        header = self.table_widget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        # Create a layout to arrange the title and table
        layout = QVBoxLayout()
        layout.addWidget(title_label)  # Add title above the table
        layout.addWidget(self.table_widget)

        # Create a QLabel for the image
        self.image_label = QLabel(self)
        self.image_label.setPixmap(QPixmap("logo-m-png.png").scaled(500, 500, Qt.KeepAspectRatio))  # Load your image and scale it

        # Create a container widget to hold the layout and image
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Add the image label to the window
        layout.addWidget(self.image_label, alignment=Qt.AlignRight | Qt.AlignTop)  # Position in the top right corner

        self.previous_quantities = {item["id"]: item["quantity"] for item in json_data}

        # Start the quantity decrease thread
        threading.Thread(target=self.decrease_quantity, daemon=True).start()

        # Start the timer to refresh the table
        self.timer = threading.Timer(1.0, self.update_table)
        self.timer.start()

    def update_table(self):
        self.table_widget.setRowCount(0)  # Clear the table
        for item in json_data:
            row_position = self.table_widget.rowCount()
            self.table_widget.insertRow(row_position)

            product_name = item["product_name"]

            current_quantity = item["quantity"]
            previous_quantity = self.previous_quantities[item["id"]]

            # Check if the quantity has decreased
            quantity_item = QTableWidgetItem(str(current_quantity))
            if current_quantity < previous_quantity:
                quantity_item.setBackground(QColor("red"))  # Highlight background in red

            # Add items to the table
            self.table_widget.setItem(row_position, 0, QTableWidgetItem(str(item["id"])))
            self.table_widget.setItem(row_position, 1, QTableWidgetItem(product_name))
            self.table_widget.setItem(row_position, 2, QTableWidgetItem(item["product_number"]))
            self.table_widget.setItem(row_position, 3, quantity_item)  # Set the quantity item
            self.table_widget.setItem(row_position, 4, QTableWidgetItem(item["delivery_unit"]))
            self.table_widget.setItem(row_position, 5, QTableWidgetItem(item["start_date"]))
            self.table_widget.setItem(row_position, 6, QTableWidgetItem(item["delivery_date"]))

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
                    item["quantity"] -= 10  # Decrease the quantity by 100
            time.sleep(1)  # Wait for 1 second before the next decrease

# Main application
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
