sudo apt-get install python3-pip -y
sudo apt-get install sqlite3 curl libsdl2-mixer-2.0-0 libsdl2-image-2.0-0 libsdl2-2.0-0 -y
python3 -m pip install -r /home/pi/monitait_watcher_jet/init/requirements.txt --break-system-packages
#write out current crontab
crontab -r # remove old crontab
crontab -l > mycron
#echo new cron into cron file
echo "@reboot sleep 60; /usr/bin/python3 /home/pi/monitait_watcher_jet/main.py &" >> mycron
#install new cron file 
crontab mycron
rm mycron
rm -rf /home/pi/monitait_watcher_jet/monitait.db
sqlite3 /home/pi/monitait_watcher_jet/monitait.db "create table monitait_table(id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL, register_id TEXT, temp_a INTEGER, temp_b INTEGER, image_path TEXT, extra_info TEXT, ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL);"
sudo raspi-config nonint do_serial_cons 1 # disable shell over serial
sudo raspi-config nonint do_serial_hw 0 # enable /dev/serial0
sudo raspi-config nonint do_expand_rootfs # expand file system to use all SD card volume