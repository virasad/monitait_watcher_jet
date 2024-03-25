sudo apt-get install python3-pip -y
sudo apt-get install git curl libsdl2-mixer-2.0-0 libsdl2-image-2.0-0 libsdl2-2.0-0 -y
python3 -m pip install python-periphery --break-system-packages
python3 -m pip install pygame --break-system-packages
#write out current crontab
crontab -l > mycron
#echo new cron into cron file
echo "@reboot sleep 60; /usr/bin/python3 /home/pi/Shoga_monitait_watcher_jet/main.py &" >> mycron
#install new cron file
crontab mycron
rm mycron