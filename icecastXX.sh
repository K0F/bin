#!/bin/bash
(startx -- `which Xvfb` :1 -screen 0 640x480x24)&
(
(sleep 10s && export DISPLAY=:1 && youtube-effect 14)&

sleep 20s

gst-launch \
  ximagesrc display-name=":1" !\
  videorate !\
  autoconvert !\
  video/x-raw-yuv,width=640,height=480,framerate=25/1 ! \
  queue !\
  vp8enc name="Kof" mode=0 threads=4 quality=3 sharpness=4 max-keyframe-distance=25 !\
  queue !\
  webmmux streamable=true name=mux\
  jackaudiosrc !\
  audioconvert !\
  audiorate !\
  audio/x-raw-float,channels=2,rate=48000,depth=16 !\
  vorbisenc quality=0.5 !\
  queue !\
  queue !\
  mux. mux. !\
  queue !\
  shout2send name="Kof's stream" ip=127.0.0.1 port=8000 password=cigareta mount=/stream.webm
)
