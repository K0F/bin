#!/bin/bash
sudo iwlist wlan0 scanning | egrep -i "ESSID|Address"
