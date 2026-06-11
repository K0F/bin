#!/bin/bash
gst-launch \
  v4l2src device=/dev/video0 always-copy=FALSE num-buffers=2000 !\
  autoconvert !\
  videorate !\
  'video/x-raw-yuv,width=640,height=360,framerate=30/1' ! \
  queue !\
  vp8enc name="Kof" mode=0 speed=4 threads=4 quality=7 sharpness=3 max-keyframe-distance=25 !\
  queue !\
  webmmux streamable=true name=mux\
  jackaudiosrc !\
  audioconvert !\
  audiorate !\
  audio/x-raw-float,channels=2,rate=48000,depth=16 !\
  vorbisenc quality=0.3 !\
  queue !\
  queue !\
  mux. mux. !\
  queue !\
  shout2send name="Kof's stream" ip=stream.iim.cz port=8000 password=pass1234 mount=/krystof.webm

