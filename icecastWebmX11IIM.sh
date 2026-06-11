#!/bin/bash
gst-launch \
  ximagesrc use-damage=1 !\
  videorate !\
  autoconvert !\
  'video/x-raw-yuv,width=1280,height=720,framerate=15/1' ! \
  queue !\
  vp8enc name="Kof" mode=1 speed=4 threads=4 quality=6 sharpness=5 max-keyframe-distance=15 !\
  queue !\
  webmmux streamable=true name=mux\
  jackaudiosrc !\
  audioconvert !\
  audiorate !\
  audio/x-raw-float,channels=2,rate=48000,depth=16 !\
  vorbisenc quality=0.5 bitrate=48000 !\
  queue !\
  queue !\
  mux. mux. !\
  queue !\
  shout2send name="test stream" ip=stream.iim.cz port=8000 password=pass1234 mount=/test.webm

