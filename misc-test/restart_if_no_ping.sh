#!/bin/bash
# Set target host IP or hostname
TARGET_HOST=192.168.1.1
count=$(ping -c 3 $TARGET_HOST | grep from* | wc -l)
if [ $count -eq 0 ]; then
    echo "$(date)" "Target host" $TARGET_HOST "unreachable, Rebooting!" >>/var/log/inetmonit.log
    /sbin/shutdown -r 0
else
    echo "$(date) ===-> OK! " >>/var/log/inetmonit.log
fi
