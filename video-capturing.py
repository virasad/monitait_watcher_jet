from periphery import GPIO
import sqlite3
import time, datetime
import datetime
import signal
import requests
import json
import socket
import serial
import glob
import os
import cv2
import numpy as np
import gauge_functions

err_msg = ""
old_err_msg = ""
image_path = ""
hostname = str(socket.gethostname())
db_connection = False
serial_connection = False
serial_rs485_connection = False
camera_connection = False
image_captured = False

# The IP camera's addresses
ip_camera_username = "admin"
ip_camera_pass = "1qaz!QAZ"
ip_camera = "192.168.1.132"
snapshot_url = f"rtsp://{ip_camera_username}:{ip_camera_pass}@{ip_camera}:554/cam/realmonitor?channel=1&subtype=0" 

# gauge_ip_camera = "192.168.101.117"
# gauge_snapshot_url = f"rtsp://{ip_camera_username}:{ip_camera_pass}@{gauge_ip_camera}:554/cam/realmonitor?channel=1&subtype=0" 

# initial_tank_volume = 0
estimated_tank_volume = -1
radius = -1
tank_volume_thresholds = 20

initial_psi = 0
estimated_psi = -1
psi_thresholds = 50

# try:
#   dbconnect = sqlite3.connect("/home/pi/monitait_watcher_jet/monitait.db")
#   cursor = dbconnect.cursor()
#   db_connection = True
# except:
#   err_msg = err_msg + "-dbs-init"
#   db_connection = False
#   pass

# # A function to get IP addr
# def get_ip_address():
#   try:
#     # Create a socket connection
#     s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     # Connect to an external server (doesn't have to be reachable)
#     s.connect(("8.8.8.8", 80))  # Google's public DNS server
#     ip_address = s.getsockname()[0]  # Get the IP address
#   except Exception as e:
#     err_msg = err_msg + "-unable-to-get-IP-address"
#   finally:
#     s.close()
  
#   return ip_address

# try:
#   ser = serial.Serial(
#         port='/dev/serial0', baudrate = 9600, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, bytesize=serial.EIGHTBITS, timeout=1)
#   serial_connection = True
#   serial_list = []
#   buffer = b''
#   last_received = ''
#   ser.flushInput()
#   extra_info = {}
#   extra_info_volume = {}
#   extra_info_gauge = {}
# except:
#   err_msg = err_msg + "-ser_init"
#   serial_connection = False
#   pass

print("initialed the parameters")
try:
      video_cap = cv2.VideoCapture(snapshot_url)
            
      if video_cap.isOpened():
            video_cap.release()
            print("The camera is ready")
            camera_connection = True
except Exception as e:
      print("error in camera initaling", e)
      camera_connection = False
      pass


# Capturing image from the IP camera
# Output video file settings
output_file = "/home/pi/monitait_watcher_jet/output_video.mp4"
desired_duration = 20  # Desired video length in seconds

try:
      video_cap = cv2.VideoCapture(snapshot_url)
      print("Starting video capture...")

      if video_cap.isOpened():
            # Get the actual frame rate of the stream
            fps = video_cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                  fps = 30  # Default to 30 fps if the frame rate is not available

            frame_width = int(video_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            frame_height = int(video_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Define the codec and create a VideoWriter object
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Codec for .mp4 files
            out = cv2.VideoWriter(output_file, fourcc, fps, (frame_width, frame_height))

            start_time = time.time()  # Record the start time
            frame_count = 0

            while (time.time() - start_time) < desired_duration:
                  ret, frame = video_cap.read()
                  if ret:
                        out.write(frame)  # Write the frame to the video file
                        frame_count += 1
                  else:
                        print("Failed to capture frame")
                        break

            video_cap.release()
            out.release()

            # Calculate actual video length
            actual_duration = frame_count / fps
            print(f"Video capture completed. Actual video length: {actual_duration:.2f} seconds")
            print("Video saved to:", output_file)

except Exception as e:
    print("Error in video capturing:", e)
