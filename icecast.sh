#!/bin/bash

#sudo dvgrab -format dv1 - | \
#    ffmpeg2theora -a 0 -v 5 -f dv -x 320 -y 240 -o /dev/stdout - | \ 
#  oggfwd -p -n "FAMU stream" localhost 8000 cigareta /theora.ogg

ffmpeg -re -f video4linux2 -i /dev/video0 -r 30 -f jack -ac 2 -i stream -vcodec libtheora -b:v 1280k -s 640x360 -acodec libvorbis -b:a 128k -threads 4 -f ogg - | oggfwd -p -n "Kof's stream" localhost 8000 cigareta /test.ogg

#ffmpeg -re -f video4linux2 -i /dev/video0 -r 15 -f jack -ac 2 -i test -vcodec libvpx -b:v 256k -s 480x270 -acodec libvorbis -b:a 128k -threads 4 -f webm http://localhost:8000/test


#ffmpeg -s 1280x720 -f video4linux2 -i /dev/video0 -f alsa -ac 2 -i hw:0,0 -b:a 128k -acodec libvorbis -vcodec libtheora -b:v 1000k -r 25 -threads 4 -f ogg - | oggfwd localhost 8000 cigareta /test.ogv
#dvgrab -format dv1 - | ffmpeg -s 800x600 -f dv -i - -b:a 128k -acodec libvorbis -vcodec libtheora -b:v 3M -r 25 -threads 4 -f ogg - | oggfwd -p -n "Hello world!" localhost 8000 cigareta /test.ogv
#dvgrab -format dv1 - | ffmpeg -f dv -i /dev/stdin -vcodec libtheora -r 25 -b:v 256k -s 480x270 -vf "yadif" -acodec libvorbis -b:a 128k -threads 4 -f ogg - | oggfwd -p -n "Informace" stream.iim.cz 8000 pass1234 /proud.ogv
