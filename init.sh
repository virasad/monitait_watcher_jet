sudo apt-get install python3-pip -y
python3 -m pip install python-periphery --break-system-packages
#write out current crontab
crontab -l > mycron
#echo new cron into cron file
echo "@reboot sleep 20; /usr/bin/python3 /home/pi/Shoga_monitait_watcher_jet/main.py &" >> mycron
#install new cron file
crontab mycron
rm mycron