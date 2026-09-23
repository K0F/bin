#!/bin/bash
FILENAME=attackers_`date +%Y%m%d`.txt
journalctl -u sshd --since today --no-pager | grep "Failed password" | grep -oE '[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}' | sort | uniq -c | sort -nr | head -n 20 | awk '{print $2}' > ~/$FILENAME
for i in `cat ~/$FILENAME`; do drop $i ; done
