#!/bin/bash
 melt ~/screen.mlt -consumer avformat real_time=1 terminate_on_pause=0 f=webm vcodec=libvpx b=2M cpu-used=4 s=1600x900 acodec=libvorbis threads=4 aq=20 | icefwd -n "Live Stream" -d "irc.freenode.net #kolektiv" -f webm localhost 8000 cigareta /live.webm
