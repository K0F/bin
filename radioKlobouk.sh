#!/bin/bash
ffmpeg -f pulse -i "alsa_output.pci-0000_00_1b.0.analog-stereo.monitor" -acodec libmp3lame -b:a 128k -content_type audio/mpeg -f mp3 icecast://source:cigareta@192.168.1.101:9000/radio.mp3
