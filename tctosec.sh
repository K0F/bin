#!/bin/bash
HO=`echo "$1" | awk -F':' '{print $1}'`
MI=`echo "$1" | awk -F':' '{print $2}'`
SE=`echo "$1" | awk -F':' '{print $3}'`
FR=`echo "$1" | awk -F':' '{print $4}'`
RESULT=`echo "($HO * 60.0 * 60.0) + ($MI * 60) + ($SE) + ($FR*0.04)" | bc -l`
echo $RESULT
