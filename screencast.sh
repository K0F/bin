#!/bin/bash
ffmpeg -f x11grab -r 25 -s 1600x900 -i :0.0+0,0 -f jack -i screencast -vcodec libx264 -crf 0 -preset ultrafast -acodec flac -ab 256k "/archive/kof/screencasts/`date +%m_%d_%H_%M`.mkv"
jack_connect supercollider screencast
