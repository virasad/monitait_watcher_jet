#!/bin/bash
for pid in $(ps -ef | awk '/order-main.py/ {print $2}'); do kill -9 $pid; done