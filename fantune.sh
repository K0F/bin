#!/bin/bash
clear

#################################################
# change the following lines to match your system
#################################################
pwmcontrol=/sys/class/hwmon/hwmon1/device/pwm1
fanrpmread=/sys/class/hwmon/hwmon1/device/fan1_input

# do not edit below this line
#################################################
log=`pwd`/fandata.log
echo "PWM,RPM" > $log

echo "This script will set your PWM to values from full power down to 0 decreasing in"
echo "approx 5 % steps and pausing 10 sec between steps to allow the fan RPM to catch"
echo "up to the new settings.  Data are logged to ${log}"
echo "which can be used to generate a graph or use as-is."

collectdata() {
  array=( 255 242 230 217 204 191 178 165 152 139 126 113 100 87 74 48 22 0 )
  for item in ${array[*]}
  do
    echo $item > $pwmcontrol
    sleep 10s
    rpm=`cat ${fanrpmread}`
    echo $item,$rpm >> $log
    echo "PWM: ${item} RPM: ${rpm}"
  done
}

/etc/rc.d/fancontrol stop
echo "1" > ${pwmcontrol}_enable

collectdata

echo "0" > ${pwmcontrol}_enable
/etc/rc.d/fancontrol start
