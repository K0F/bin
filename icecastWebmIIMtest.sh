#!/bin/bash
gst-launch \
  videotestsrc pattern=10 !\
  autoconvert !\
  videorate !\
  video/x-raw-yuv,width=1280,height=720,framerate=25/1 ! \
  queue !\
  vp8enc name="Kof" mode=1 speed=4 threads=4 quality=4 sharpness=3 max-keyframe-distance=50 !\
  queue !\
  webmmux streamable=true name=mux\
  jackaudiosrc connect=0 do-timestamp=TRUE !\
  audioconvert !\
  audiorate !\
  audio/x-raw-float,channels=2,rate=48000,depth=16 !\
  vorbisenc quality=0.3 !\
  queue !\
  queue !\
  mux. mux. !\
  queue !\
  shout2send name="Kof's stream" ip=stream.iim.cz port=8000 password=pass1234 mount=/krystof.webm

