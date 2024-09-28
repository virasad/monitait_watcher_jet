import time
import threading
import json
from rich.console import Console
from rich.table import Table
from rich.live import Live

# Initial data (the same as before)
data = (5, 'ZR2024092203', '[{"id": 163, "start_date": "2019-08-24T14:15:22Z", "delivery_date": "2019-08-24T14:15:22Z", "quantity": 3096, "delivery_unit": "CAR", "product_name": "\\u0645\\u0627\\u06cc \\u0628\\u06cc\\u0628\\u06cc", "product_number": "20240819", "default_ids": ["1234567891111"], "description": "TEST", "batches": [{"quantity": "3096", "batch_uuid": "a8715fb9-7b72-4d28-b0c3-7723f43b7f6d", "assigned_id": "1234567891111"}], "status": "not_started", "batch_status": "view"}, {"id": 164, "start_date": "2019-08-24T14:15:22Z", "delivery_date": "2019-08-24T14:15:22Z", "quantity": 3200, "delivery_unit": "CAR", "product_name": "\\u062f\\u0633\\u062a\\u0645\\u0627\\u0644 \\u0645\\u0631\\u0637\\u0648\\u0628", "product_number": "20240820", "default_ids": ["1234567892222"], "description": "TEST", "batches": [{"quantity": "3200", "batch_uuid": "bfc9d47a-ff2e-492e-9dd2-0eca1613dd68", "assigned_id": "1234567892222"}], "status": "not_started", "batch_status": "view"}, {"id": 165, "start_date": "2019-08-24T14:15:22Z", "delivery_date": "2019-08-24T14:15:22Z", "quantity": 3300, "delivery_unit": "CAR", "product_name": "\\u06a9\\u0644\\u06cc\\u0646 \\u0627\\u067e", "product_number": "20240821", "default_ids": ["1234567893333"], "description": "TEST", "batches": [{"quantity": "3300", "batch_uuid": "f0c24da2-afe9-4cfa-9a94-ab72168d025a", "assigned_id": "1234567893333"}], "status": "not_started", "batch_status": "view"}]', 0)

# Parse the JSON string into a Python list of dictionaries
json_data = json.loads(data[2])

# Function to create the table
def create_table():
    table = Table(title="Product Information (Live Updates)")

    # Define columns
    table.add_column("ID", style="cyan", justify="center")
    table.add_column("Product Name", style="magenta")
    table.add_column("Product Number", style="green")
    table.add_column("Quantity", justify="right")
    table.add_column("Delivery Unit", style="yellow")
    table.add_column("Start Date", style="blue")
    table.add_column("Delivery Date", style="blue")
    table.add_column("Status", style="red")

    # Populate the table with current data
    for item in json_data:
        table.add_row(
            str(item["id"]),
            item["product_name"].encode('utf-8').decode('unicode_escape'),
            item["product_number"],
            str(item["quantity"]),
            item["delivery_unit"],
            item["start_date"],
            item["delivery_date"],
            item["status"]
        )

    return table

# Function to simulate quantity decrease
def decrease_quantity():
    while True:
        for item in json_data:
            if item["quantity"] > 0:
                item["quantity"] -= 10  # Decrease the quantity by 100
        time.sleep(1)  # Wait for 1 second before the next decrease

# Create a thread to handle the quantity changes
def run_quantity_decrease():
    threading.Thread(target=decrease_quantity, daemon=True).start()

# Main function to display the live table
def main():
    console = Console()

    # Start the thread that decreases quantity
    run_quantity_decrease()

    # Live context to auto-refresh the table
    with Live(create_table(), console=console, refresh_per_second=4) as live:
        while True:
            time.sleep(1)  # Let the thread work for a second
            live.update(create_table())  # Update the live table

# Run the main function
if __name__ == "__main__":
    main()