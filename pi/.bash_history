raspi-config
sudo raspi-config
clear
reset
sudo raspi-config
hostname -I
sudo apt full-upgrade
sudo apt-get install apache2 php libapache2-mod-php php-sqlite3 sqlite pijuice-base dnsmasq hostapd git python3-pip python3-flask -y
sudo apt-get install apache2 php libapache2-mod-php php-sqlite3 sqlite pijuice-base dnsmasq hostapd git python3-pip python3-flask i2c-tools -y 
sudo apt update
apt-key list | grep -A4 "trusted.gpg$"
sudo apt-key export A0DA38D0 | sudo gpg --dearmor -o /tmp/raspi.gpg
sudo apt-key export 90FDDD2E | sudo gpg --dearmor -o /tmp/raspi.gpg
file /tmp/raspi.gpg
sudo apt-key del 90FDDD2E
sudo mv /tmp/raspi.gpg /etc/apt/trusted.gpg.d/
sudo apt update && sudo apt full-upgrade -y && sudo apt-get install apache2 php libapache2-mod-php php-sqlite3 sqlite pijuice-base dnsmasq hostapd git python3-pip python3-flask i2c-tools -y
ip a show wlan0
sudo nano /etc/dhcpcd.conf
sudo nano /etc/dnsmasq.conf
sudo nano /etc/hostapd/hostapd.conf
sudo nano /etc/default/hostapd
cat /usr/share/doc/hostapd/README.Debian
sudo systemctl unmask hostapd
sudo nano 
sudo nano /etc/sysctl.conf
sudo sysctl -p
sudo nano/etc/network/interfaces
sudo nano /etc/network/interfaces
ls /etc/network
sudo systemctl enable hostapd@hostapd
sudo systemctl start hostapd@hostapd
sudo sed -i 's/^net.ipv4.ip_forward=1/net.ipv4.ip_forward=0/' /etc/sysctl.conf
sudo sysctl -p
cat /proc/sys/net/ipv4/ip_forward
sudo nano /etc/dhcpcd.conf
cat /etc/dnsmasq.conf
sudo iptables -t nat -F
sudo systemctl restart dhcpcd
sudo systemctl restart dnsmasq
sudo systemctl restart hostapd@hostapd
sudo apt install dhcpd iptables
sudo apt install dhcpcd iptables
sudo systemctl restart dhcpcd
sudo iptables -t nat -F
systemctl status hostapd@wlan0
systemctl status hostapd@hostapd
sudo systemctl start hostapd@hostapd
systemctl status hostapd@hostapd
systemctl status hostapd
journalctl -u hostapd --no-pager | tail -30
ip link show wlan0
sudo hostapd -dd /etc/hostapd/hostapd.conf
sudo systemctl restart hostapd
sudo systemctl restart dhcpcd
systemctl status hostapd
hostname -I
sudo ip addr add 192.168.5.1/24 dev wlan0
nano /home/pi/startup.sh
chmod 777 /home/pi/startup.sh 
sudo nano /etc/systemd/system/startup.service
sudo systemctl daemon-reload
sudo systemctl enable startup.service
sudo systemctl start startup.service
systemctl status startup.service
sudo nano /home/pi/startup.sh
sudo nano /etc/systemd/system/startup.service
sudo systemctl daemon-reload
sudo systemctl restart startup.service
systemctl status startup.service
python3 servertest.py 
sudo apt install python3-waitress
sudo apt update
ping google.com
hostname -I
sudo nano /etc/pip.conf
pip3 install waitress
history
sudo systemctl restart dnsmasq
pip3 install waitress
sudo iptables -t nat -F
cat /etc/dnsmasq.conf
sudo nano /etc/dhcpcd.conf
sudo nano /etc/dnsmasq.conf
history
sudo nano /etc/dhcpcd.conf
sudo reboot
sudo shutdown -h 0
pip3 install waitress
python3 servertest.py 
hostname -I
sudo systemctl start startup.service 
hostname -I
python3 servertest.py 
sudo nano /etc/dhcpcd.conf
hostname -I
sudo nano /etc/dnsmasq.conf
sudo systemctl start startup.service 
sudo systemctl restart startup.service 
python3 servertest.py 
echo Hi
sudo shutdown -h 0
sudo systemctl stop systemd
systemctl
hostname -I
ls
nano startup.sh 
sudo systemctl status startup.service 
./startup.sh 
sudo ./startup.sh 
systemctl status hostapd
systemctl status hostapd@hostapd.service 
hostname -I
systemctl stop hostapd
sudo systemctl restart hostapd@hostapd.service 
sudo systemctl status hostapd@hostapd
sudo systemctl status hostapd
sudo systemctl start hostapd
sudo systemctl status hostapd
hostname -I
sudo nano /etc/dhcpcd.conf
sudo nano /etc/hostapd/
sudo nano /etc/hostapd/hostapd.conf 
python3 servertest.py 
+
-+
-
sudo chmod -R 777 /var/www 
sudo systemctl restart apache2.service 
php
sudo apt install libapache2-mod-php
sudo apt install lsb-release
sudo apt install lsb-releasesudo apt update && sudo apt upgrade -y sedrasdf
sudo apt update && sudo apt upgrade -ysudo apt update && sudo apt upgrade -y
sudo apt update && sudo apt upgrade -y
ping google.com
iwconfig
sudo apt install php-sqlite
ping google.com
nano
sudo nano /etc/resolve.conf
ping google.com
ping 8.8.8.8
sudo systemctl restart dnsmasq.service 
ping google.com
sudo apt-cache search php sqlite
sudo apt install php-sqlite3
sudo apt install php-db
route -n
ping -c3 google.com
hostname -I
traceroute 8.8.8.8
sudo nano /etc/network/interfaces
sudo nano /etc/dhcpcd.conf
sudo nano /etc/resolv.conf.head
sudo reboot
python3 servertest.py 
sudo shutdown -h 0
journalctl -b
grep FAILED /var/log/boot.log : more
cat /var/log/boot.log
ls /var/log/
cat README
cat /var/log/READM
cat /var/log/README 
journalctl
dmesg | less
dmesg
journalctl -b
sudo apt install php-db
sudo apt update 
sudo journalctl -u hostapd --no-pager | tail -20
iw list
iw dev wlan0 info
iw dev wlan0 station dump
sudo nano /etc/hostapd/hostapd.conf
sudo journalctl -u hostapd --no-pager | tail -20
sudo systemctl status hostapd@hostapd.service
sudo systemctl restart hostapd@hostapd.service
journalctl -xeu hostapd@hostapd.service
q
sudo systemctl restart hostapd@hostapd.service
journalctl -xeu hostapd@hostapd.service
sudo systemctl status hostapd@hostapd.service
sudo journalctl -u hostapd --no-pager | tail -20
sudo systemctl restart hostapd
sudo systemctl disable hostapd@hostapd
sudo apt remove php-d
sudo apt remove php-db
sudo systemctl restart apache2
cd /var/www/html/
cd ..
sudo chmod -R 777
sudo chmod -R 777 *
sudo systemctl restart hostapd
sudo systemctl status hostapd
sudo systemctl restart hostapd
sudo systemctl status hostapd
sudo systemctl restart hostapd
sudo systemctl status hostapd
wi
iw
iw 
iw dev wlan0 info
sudo systemctl restart hostapd
iw dev wlan0 info
sudo systemctl status hostapd
sudo update-rc.d hostapd enable
sudo systemctl status hostapd
/etc/init.d/hostapd restart
sudo ./etc/init.d/hostapd restart
sudo /etc/init.d/hostapd restart
lspci -k | grep -A 3 -i network
sudo systemctl restart NetworkManager
dmesg | grep wlan0
sudo iwconfig wlan0 power off
sudo ifconfig wlan0 down
sudo ifconfig wlan0 up
sudo apt update && sudo apt upgrade
sudo /etc/init.d/hostapd restart
sudo systemctl status hostapd
cd Downloads
ls
cqd
cwd
cd ..
cd pi
wget -N https://www.dwservice.net/download/dwagent.sh
sudo bash dwagent.sh
python3 servertest.py 
hostname -I~
hostname -I
python3 servertest.py 
systemctl status hostapd
sudo systemctl restart hostapd
systemctl status hostapd
lsmod
dmesg | grep wlan0
ip link show
hostname -I
sudo rpi-update
sudo reboot
systemctl status hostapd
python3 servertest.py 
systemctl status hostapd
journalctl hostapd
journalctl
q
sudo systemctl restart hostapd
systemctl status hostapd
iw config
iw info
iw wlan0
iw wlan0 info
nano readsht.py
python3 readsht.py 
pip3 install numpy
hostapd hostapd
hostapd
python3 readsht.py 
and make sure that they are the versions you expect.
Please carefully study the documentation linked above for further help.
Original error was: libopenblas.so.0: cannot open shared
and make sure that they are the versions you expect.
Please carefully study the documentation linked above for further help.
Original error was: libopenblas.so.0: cannot open sharedsudo apt-get install libopenblas-devsudo apt-get install libopenblas-dev
sudo apt-get install libopenblas-dev
python3 readsht.py 
nano readsht.py
python3 readsht.py 
nano readsht.py
python3 readsht.py 
nano readsht.py
python3 readsht.py 
nano readsht.py
python3 readsht.py 
nano readsht.py
python3 readsht.py 
nano readsht.py
python3 readsht.py 
nano readsht.py
python3 readsht.py 
python3 testinghandle.py 
nano testinghandle.py
from flask_cors import CORS
CORS(app)
nano testinghandle.py
pip3 install flask_cors
nano testinghandle.py
cat testinghandle.py 
systemctl status hostapd
sudo shutdown -h 0
systemctl status hostapd
sudo systemctl start startup.service 
systemctl status hostapd
sudo systemctl restart hostapd
systemctl status hostapd
sudo systemctl restart hostapd
hostname -I
python3 servertest.py 
hostname -I
sudo systemctl restart hostapd@hostapd
sudo systemctl status hostapd
journalctl -u hostapd --no-pager | tail -20
ps aux | grep wpa_supplicant
sudo systemctl stop wpa_supplicant
sudo systemctl disable wpa_supplicant
sudo systemctl stop wpa_supplicant
sudo systemctl restart hostapd@hostapd
sudo systemctl restart hostapd
python3 servertest.py 
hostname -I
sudo systemctl start startup.service 
python3 servertest.py 
sudo systemctl status wpa_supplicant.service 
sudo apt remove wpa_supplicant
rm -rf /lib/systemd/system/wpa_supplicant.service
sudo rm -rf /lib/systemd/system/wpa_supplicant.service
/sbin/wpa_supplicant
sudo rm -rf /sbin/wpa_supplicant
sudo systemctl restart hostapd
python3 servertest.py 
sudo apt remove --purge wpa_supplicant
python3 servertest.py 
hostname -I
python3 servertest.py 
tail /var/www/html/Error_log.txt 
systemctl status apache2
sudo systemctl restart apache2
systemctl status apache2
sudo reboot
tail /var/www/html/Error_log.txt 
sudo ip addr add 192.168.5.1/24 dev wlan0
ls /dev/tty*
python3 pymod.py 
pip3 install pymodbus
.
php -v
sudo apt install php libapache2-mod-php php-sqlite3
sudo a2enmod php
ls /etc/apache2/mods-available | grep php
sudo a2enmod php8.1
sudo a2enmod php8.2
sudo systemctl restart apache2
php -l /var/www/html/index.php
sudo chmod -R 777 /var/www/
sudo nano /etc/php/*/apache2/php.ini
sudo tail -f /var/log/apache2/error.log
sudo chown www-data:www-data /home/pi/example.db
sudo chmod 777 /home/pi/example.db
sudo tail -f /var/log/apache2/error.log
ls -l /home/pi/example.db
sudo chmod 755 /home/pi
sudo systemctl restart apache2
sudo tail -f /var/log/apache2/error.log
sudo systemctl restart hostapd
hostname -I
python3 servertest.py 
python3 servertesting.py 
sudo mv example.db /var/www/example.db
sudo mv /var/www/example.db /var/www/html/example.db
sudo python3 pymod.py 
pip3 install pymodbus
sudo python3 pymod.py 
python3 pymod.py 
pip3 install pyserial
python3 pymod.py 
ls /dev/ttyUSB*
python3 pymod.py 
sudo python3 pymod.py 
pip3 install pymodbus pyserial
python3 pymod.py 
sudo pip3 install pymodbus pyserial
sqlite3 /home/pi/example.db .dump > /tmp/dump.sql
sqlite3 /var/www/example.db < /tmp/dump.sql
sqlite3 /var/www/example.db
hostname -I
sudo ip addr add 192.168.5.1/24 dev wlan0
sudo systemctl restart hostapd
python3 servertesting.py 
ls /home/pi
sudo ip addr add 192.168.5.1/24 dev wlan0
sudo systemctl restart hostapd
python3 servertesting.py 
sudo shutdown -h 0
sudo namo /etc/hostapd/hostapd.conf 
sudo nano /etc/hostapd/hostapd.conf 
ls
bash dwagent.sh 
sudo bash dwagent.sh 
dwagent
rm -rf /usr/share/dwagent
python3 /usr/share/dwagent/configure.py 
sudo python3 /usr/share/dwagent/configure.py 
sudo systemctl status dwagent.service 
sudo python3 /usr/share/dwagent/configure.py 
tree /usr/share/dwagent
ls /usr/share/dwagent
cd /usr/share/dwagent/
python3 configure.py
hostname -I
sudo ip addr add 192.168.5.1/24 dev wlan0
hotstname -I
hostname -I
sudo ip addr add 192.168.5.1/24 dev wlan0
sudo systermctl restart sudo systemctl restart hostapd
sudo systemctl restart hostapd
python3 servertesting.py
hostname -I
python3 servertesting.py 
shutdown -h 0
sudo ip addr add 192.168.5.1/24 dev wlan0
sudo systemctl restart hostapd
python3 servertesting.py 
sudo systemctl restart hostapd
python3 servertesting.py 
hostname -I
sudo systemctl restart hostapd
python3 servertesting.py 
reboot
sudo nano /etc/hostapd/hostapd.conf
sudo ip addr add 192.168.5.1/24 dev wlan0
sudo systemctl restart hostapd
python3 servertesting.py 
systemctl status hostapd.service 
sudo systemctl restart hostapd
systemctl status hostapd.service 
sudo nano /etc/hostapd/hostapd.conf
hostname -h
hostname -b logger-2
sudo hostname -b logger-2
logout
sudo systemctl restart hostapd
sudo ip addr add 192.168.5.1/24 dev wlan0
sudo systemctl restart hostapd
systemctl status hostapd.service 
sudo systemctl restart hostapd
python3 servertesting.py 
reset
sudo reboot
sudo raspi-config
systemctl status hostapd.service 
sudo systemctl restart hostapd
systemctl status hostapd.service 
python3 gpiotest.py 
sudo apt-get install python3-pijuice
sudo apt update
sudo systemctl restart apache2
history
history 
nano ~/.bashrc
sudo nano /etc/rc.local
chmod +x /path/to/your/script.sh
chmod +x start.sh
chmod 777 start.sh
chmod +x start.sh
sudo reboot
sudo ip addr add 192.168.5.1/24 dev wlan0
sudo systemctl restart hostapd
python3 servertesting.py 
hostname -I
python3 servertesting.py 
pip install ntplib
python3 servertesting.py 
pip install psutil
python3 servertesting.py 
history
sudo reboot
systemctl status startup.service 
sudo systemctl daemon-reload
sudo systemctl disable startup.service 
start.sh
./start.sh
sudo nano /etc/systemd/system/getty@tty1.service.d/override.conf
sudo systemctl daemon-reload
sudo reboot
ifconfig
sudo reboot
ifconfig
sudo reboot
systemctl status hostapd.service
sudo reboot
sudo ip addr add 192.168.5.1/24 dev wlan0
sudo nano /etc/systemd/system/getty@tty1.service.d/override.conf
sudo reboot
sudo nano /etc/systemd/system/getty@tty1.service.d/override.conf
sudo systemctl daemon-reload
sudo systemctl restart getty@tty1.service
sudo systemctl enable getty@tty1.service
sudo nano /etc/systemd/system/getty@tty1.service.d/override.conf
sudo nano start.sh
sudo systemctl daemon-reload
sudo systemctl restart getty@tty1.service
hostname -I
sudo systemctl status hostapd
sudo systemctl restart hostapd
sudo reboot
sudo nano start.sh
sudo reboot
tail nohup.out
ls
cat nohup.out
sudo nano start.sh
sudo reboot
sudo apt install tmux
sudo systemctl restart hostapd
sudo systemctl restart getty@tty1.service
sudo nano /etc/systemd/system/getty@tty1.service.d/override.conf
sudo systemctl restart getty@tty1.service
systemctl daemon-reload
sudocsystemctl daemon-reload
sudo systemctl daemon-reload
sudo systemctl restart getty@tty1.service
./restart.sh
chmod +x *
./restart.sh
sudo reboot
hostname -I
sudo ip addr add 192.168.5.1/24 dev wlan0
sudo systemctl restart hostapd.service 
./setup.sh
history
# Function to check the IP address
def check_ip():
# Function to add IP address if necessary
def configure_ip():
sudo nano /etc/systemd/system/startup.service
systemctl enable startup.service
sudo systemctl daemon-reload
systemctl start startup.service
sudo systemctl start startup.service
sudo systemctl status startup.service
sudo systemctl stop startup.service
sudo nano /etc/systemd/system/startup.service
systemctl disable startup.service
sudo systemctl disable startup.service
sudo nano /etc/init/tty.conf
ls /etc/init
sudo systemctl stop getty
sudo systemctl stop getty@tty2
sudo systemctl stop getty@tty7
sudo systemctl stop getty@tty3
sudo systemctl stop getty@tty4
sudo systemctl stop getty@tty5
sudo systemctl stop getty@tty6
sudo systemctl stop getty@tty7
sudo systemctl stop getty@tty8
sudo systemctl stop getty@tty2
sudo systemctl stop *@tty2
sudo pip3 install flask_cors
sudo systemctl stop *@tty2
sudo pip3 install waitress, ntplib, os, time, json, copy, shutil, logging, platform, sqlite3, requests, threading, sys, subprocess
sudo pip3 install waitress ntplib os time json copy shutil logging platform sqlite3 requests threading sys subprocess
sudo pip3 install waitress ntplib  json copy shutil logging platform sqlite3 requests threading sys subprocess
sudo pip3 install waitress ntplib copy shutil logging platform sqlite3 requests threading sys subprocess
sudo pip3 install waitress ntplib platform sqlite3 requests threading sys subprocess
sudo pip3 install waitress ntplib requests
sudo pip3 install psutil
pythom3 servertesting.py 
python3 servertesting.py 
openvt
openvt -u pi -s -- python3 servertesting.py 
openvt -s -- python3 servertesting.py 
sudo openvt -u pi -s -- python3 servertesting.py 
sudo openvt -u pi -se -- python3 servertesting.py 
sudo openvt -u pi -se python3 servertesting.py 
sudo openvt -se python3 servertesting.py 
sudo openvt -sef python3 servertesting.py 
sudo openvt -sf python3 servertesting.py 
sudo openvt -u pi -sf python3 servertesting.py 
sudo openvt -sf python3 servertesting.py 
history
sudo nano /etc/init/tty.conf
sudo nano /etc/systemd/system/startup.service
sudo nano /etc/systemd/system/getty@tty1.service.d/override.conf
sudo reboot
sudo openvt -sf python3 servertesting.py 
sudo nano /etc/rc.local
sudo rm /etc/rc.local
sudo nano /etc/rc.local
sudo chmod 755 /etc/rc.local
dir -C -h -l -s /etc/rc.*
sudo nano /etc/rc.local
sudo nano /etc/systemd/logind.conf
sudo nano /etc/rc.local
sudo systemctl is-enabled rc-local.service
sudo systemctl status rc-local.service
sudo systemctl enable rc-local.service
sudo nano /etc/rc.local
sudo systemctl cat rc-local.service 
sudo reboot
sudo nano /etc/rc.local
sudo systemctl restart rc.local
sudo systemctl restart rclocal
sudo systemctl restart rc-local
sudo nano /etc/rc.local
chmod +x /home/pi/servertesting.py
tail /var/log/messages
tail /var/log/syslog
ls /var/log
sudo systemctl disable rc-local.service
sudo systemctl mask rc-local.service
systemctl status startup.service 
systemctl nano startup.service 
systemctl cat startup.service 
sudo systemctl start startup.service 
sudo systemctl status startup.service 
sudo journalctl -u startup.service
systemctl cat startup.service 
sudo nano /etc/systemd/system/startup.service
sudo systemctl start startup.service 
systemctl daemon-reload
sudo system
sudo systemctl restart startup.service 
sudo systemctl status startup.service 
sudo journalctl -u startup.service
sudo journalctl --unit=startup.service --flush
sudo systemctl restart startup.service 
sudo journalctl -u startup.service
sudo journalctl --unit=startup.service --rotate --vacuum-time=1s
sudo systemctl restart startup.service 
sudo journalctl -u startup.service
sudo reboot
sudo openvt -sf python3 servertesting.py 
sudo systemctl enable startup.service
sudo reboot
sudo journalctl -u startup.service
sudo nano /etc/systemd/system/startup.service
sudo systemctl daemon-reload
sudo systemctl restart startup.service 
sudo nano /etc/systemd/system/startup.service
sudo systemctl daemon-reload
sudo systemctl restart startup
./startup.sh
./setup.sh
history
cd /usr/share/dwagent/
python3 configure.py 
cd
nano setup.sh
./setup.sh
nano setup.sh
./setup.sh
sudo raspi-config
pijuice-cli
pijuicecli
pijuice_cli
./setup.sh
sudo raspi-config
ls
python3 readsht.py 
python3 pymod.py 
ls /dev/ttyUSB
ls /dev/ttyUS
ls /dev/tty
ls /dev/tty*
python3 pymod.py 
tail -f /var/www/html/server.log 
