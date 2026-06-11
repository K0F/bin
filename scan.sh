#!/bin/bash
# Scan APs with 'iw' and output to single-line. 
# CSV is in the format:
#   BSSID, freq (MHz), RSSI (dBms), ESSID, channel) 
# Tested with iw version 3.15 on OpenWrt and 3.4 on Debian GNU/Linux

DATA=/tmp/data
NIC=$(iw dev | grep Interface | awk '{ print $2 }')
TMPFILE=/tmp/scan.log
SCAN=$DATA/networks
S=1;E=5;

# Scrape 'iw' scan output and write to temporary file
iw dev $NIC scan | grep -E '^BSS|SSID|DS Parameter set: channel|signal:|freq:'\
| sed -e 's/BSS\ //' -e 's/(on.*$//'  -e 's/DS Parameter\ set:\ channel\ // ' \
-e 's/SSID:\ //' -e 's/freq://' -e 's/signal: //' -e 's/dBm//'\
    > $TMPFILE && LEN=$(cat $TMPFILE | wc -l)

# Count lines in 5's
for i in $(seq 1 $((LEN/5)))
    do
        LINES=$(sed -n "$S,$E p;$E q" $TMPFILE)
        # Test for hidden ESSIDs. Allow for ESSIDs with spaces
        if [ $(echo $LINES | awk '{print substr($0, index($0,$4))}' | sed \
            's/\(.*\)[[:space:]].*/\1/' | wc -c )  -gt 1 ]
            then
                # Replace all whitespace with commas except whitespace in
                # ESSID field
                echo $LINES | awk -F ' ' -v OFS=',' '{print $1, $2, $3, \
                substr($0, index($0,$4))}' | sed 's/\(.*\)[[:space:]]/\1,/'
        fi
        # Increment
            ((S+=5))
            ((E+=5))
    done > $SCAN
rm $TMPFILE
