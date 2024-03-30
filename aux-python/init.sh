sudo apt-get install python3-pip -y
python3 -m pip install python-periphery --break-system-packages
python3 -m pip install pyserial --break-system-packages
python3 -m pip install pygame --break-system-packages
#write out current crontab
crontab -l > mycron
#echo new cron into cron file
echo "@reboot sleep 60; /usr/bin/python3 /home/pi/Shoga_monitait_watcher_jet/main.py & ; /usr/bin/python3 /home/pi/Shoga_monitait_watcher_jet/main-serial.py &" >> mycron
#install new cron file
crontab mycron
rm mycron
sudo raspi-config nonint do_serial_cons 1
sudo raspi-config nonint do_serial_hw 0
sudo raspi-config nonint do_expand_rootfs