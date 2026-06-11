#!/bin/bash
youtube-upload -m krystof.pesek@gmail.com -p cigareta66 -t "archive `getTime.sh $1`" -d "`mediainfo $1`" -c Education "$1"
