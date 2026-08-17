#!/bin/bash
set +x
if cd /usr/share/dwagent/ 2>/dev/null; then
    cd
    sudo dwagent_uninstall
fi

echo "========================================="
echo "Raspberry Pi Initial Setup Script"
echo "========================================="
echo ""

# WiFi Configuration
echo "Configure WiFi (hostapd):"
read -p "Enter WiFi SSID: " wifi_ssid

# Create hostapd.conf
echo "Writing hostapd configuration..."
sudo tee /etc/hostapd/hostapd.conf > /dev/null <<EOF
interface=wlan0
ssid=$wifi_ssid
hw_mode=g
channel=6
ieee80211n=1
wmm_enabled=1
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase=12345678
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF

echo "✓ hostapd.conf configured"
echo ""

# Hostname Configuration
echo "Configure system hostname:"
read -p "Enter hostname: " new_hostname

echo "Setting hostname to: $new_hostname"
echo "$new_hostname" | sudo tee /etc/hostname > /dev/null
sudo hostnamectl set-hostname "$new_hostname"

echo "✓ Hostname configured"
echo ""

# Show IP Address
echo "Current IP configuration:"
hostname -I
echo ""

# Tailscale Setup
echo "Would you like to set up Tailscale? (y/n)"
read -r tailscale_response
if [ "$tailscale_response" = "y" ] || [ "$tailscale_response" = "Y" ]; then
    echo "Installing and setting up Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
    echo "Starting Tailscale - follow instructions..."
    tailscale up
    echo "✓ Tailscale configured"
fi

echo ""
echo "========================================="
echo "Setup complete! System will reboot in 3 seconds..."
echo "========================================="
sleep 3
sudo reboot -h now