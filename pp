#!/bin/bash
SKETCH=`pwd`
OUTPUT=/tmp/processingMess/

killall processing-java || echo No instances running, good.
cd "/home/kof/processing-git/build/linux/work" && ./processing-java --sketch="$SKETCH" --output=$OUTPUT --force --run
cd $SKETCH

