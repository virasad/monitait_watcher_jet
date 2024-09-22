#!/bin/bash
for pid in $(ps -ef | awk '/order-main.py/ {print $2}'); do kill -9 $pid; done
for pid in $(ps -ef | awk '/order_main_shipment.py/ {print $2}'); do kill -9 $pid; done