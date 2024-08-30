#!/bin/bash
#melt "$@" -consumer avformat real_time=1 terminate_on_pause=0 f=webm vcodec=libvpx b=1500k cpu-used=4 s=640x360 threads=4 acodec=libvorbis aq=20 | icefwd -n "Live Stream" -d "irc.freenode.net #kolektiv" -f webm localhost 8000 cigareta /live.mkv
melt "$@" -consumer avformat real_time=1 terminate_on_pause=0 s=1024x576 f=webm vcodec=libvpx b=5000k cpu-used=4  threads=4 acodec=libaac movflags="faststart" aq=20 | icefwd -n "Live Stream" -d "irc.freenode.net #kolektiv" -f webm localhost 8000 cigareta /live.mkv
