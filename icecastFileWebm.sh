#!/bin/bash
gst-launch \
  filesrc location="$1" !\
  decodebin !\
  autoconvert !\
  videorate !\
  video/x-raw-yuv,width=640,height=360,framerate=30/1 ! \
  queue !\
  vp8enc name="Kof" mode=0 speed=4 threads=4 quality=6 sharpness=3 max-keyframe-distance=30 !\
  queue !\
  webmmux streamable=true name=mux\
  mux. !\
  queue !\
  shout2send name="Kof's stream" ip=localhost port=8000 password=cigareta mount=/test.webm

