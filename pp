#!/bin/bash
SKETCH=`pwd`
OUTPUT=/tmp/processingMess/

killall processing || echo No instances running, good.
cd "/var/lib/snapd/snap/bin/" && ./processing cli --sketch="$SKETCH" --output=$OUTPUT --force --run
cd $SKETCH

