#!/bin/bash
#ffmpeg -f lavfi -i testsrc=duration=1000:size=640x360:rate=25 -vf "[in]yadif[a],[a]scale=640x360[out]" -vcodec theora -r 25 -b:v 1M -acodec libvorbis -b:a 128k -threads 4 -f ogg - | oggfwd -p -n "test" stream.iim.cz 8000 pass1234 /test
dvgrab -r --format mpeg2 - | ffmpeg -f mpegts -i /dev/stdin -vcodec theora -r 25 -b:v 900k -vf "scale=480x320" -acodec libvorbis -b:a 128k -threads 4 -f ogg - | oggfwd -p -n "NTK" stream.iim.cz 8000 pass1234 /ntk
