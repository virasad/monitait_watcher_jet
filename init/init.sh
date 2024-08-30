sudo apt-get install python3-pip -y
sudo apt-get install sqlite3 curl libsdl2-mixer-2.0-0 libsdl2-image-2.0-0 libsdl2-2.0-0 -y
sudo apt-get install python3-opencv -y
python3 -m pip install -r /home/pi/monitait_watcher_jet/init/requirements.txt --break-system-packages
sudo cp /home/pi/monitait_watcher_jet/init/monitait-watcher-jet.service /lib/systemd/system/
sudo chmod 644 /lib/systemd/system/monitait-watcher-jet.service
chmod +x /home/pi/monitait_watcher_jet/main.py
rm -rf /home/pi/monitait_watcher_jet/monitait.db
# sqlite3 /home/pi/monitait_watcher_jet/monitait.db "create table monitait_table(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, register_id TEXT, temp_a INTEGER, temp_b INTEGER, image_number INTEGER, extra_info TEXT, ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL);"
sudo raspi-config nonint do_serial_cons 1 # disable shell over serial
sudo raspi-config nonint do_serial_hw 0 # enable /dev/serial0
sudo raspi-config nonint do_expand_rootfs # expand file system to use all SD card volume
sudo systemctl daemon-reload
sudo systemctl enable monitait-watcher-jet.service
sudo systemctl start monitait-watcher-jet.service