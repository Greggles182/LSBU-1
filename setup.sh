#!/bin/bash
set +x
cd /usr/share/dwagent/
echo "Follow user manual to configure the agent"
sleep 5
python3 configure.py
echo "Agent configured"
echo "Change LOG-* to required"
sleep 5
sudo nano /etc/hostapd/hostapd.conf
echo "Change hostname to required"
sleep 5
sudo nano /etc/hostname
echo "Set up"
hostname -I
echo "Will now reboot"
sleep 3
sudo reboot -h now