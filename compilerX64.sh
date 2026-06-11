#!/bin/bash
# file /home/pi/s-x86compiler.sh
echo "removing arm compiler links to use defualt x86 again"
cd /home/kof/tools/arm-bcm2708/gcc-linaro-arm-linux-gnueabihf-raspbian-x64/bin/bin
rm c++ cpp g++ gcc cc
