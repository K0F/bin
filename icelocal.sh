#!/bin/bash
melt "$@" -consumer avformat real_time=1 terminate_on_pause=0 f=ogg vcodec=libtheora b=1500k s=640x360 acodec=libvorbis aq=20 | icefwd -n "Live Stream" -d "irc.freenode.net #kolektiv" -f ogg localhost 8000 cigareta /live.ogg
