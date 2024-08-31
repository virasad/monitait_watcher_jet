# Ping to the router
ping -c2 watcher-api.virasad.ir > /dev/null

# If the return code from ping ($?) is not 0 (meaning there was an error)
if [ $? != 0 ]; then
    # Restart the wireless interface
    pkill -f requests-watcher.py
    ifdown --force wlan0
    sleep 5
    ifup wlan0
    systemctl restart systemd-resolved.service
    python3 requests-watcher.py
fi
