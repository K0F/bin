#!/bin/bash
# file /home/pi/s-arm-compiler.sh 
echo 'linking gcc to arm-gcc with ln -s'
cd /home/kof/rpi-tools/arm-bcm2708/gcc-linaro-arm-linux-gnueabihf-raspbian-x64/bin
ln -s arm-linux-gnueabihf-gcc gcc
ln -s arm-linux-gnueabihf-gcc cc
ln -s arm-linux-gnueabihf-c++ c++
ln -s arm-linux-gnueabihf-cpp cpp
ln -s arm-linux-gnueabihf-g++ g++
