#!/bin/bash
XID=`xdotool selectwindow getwindowgeometry --shell`;
echo $XID
gst-launch \
  ximagesrc use-damage=1 !\
  videorate !\
  autoconvert !\
  video/x-raw-yuv,width=1600,height=900,framerate=5/1 ! \
  queue !\
  vp8enc name="Kof" mode=1 speed=4 threads=4 quality=5 sharpness=4 max-keyframe-distance=5 !\
  queue !\
  webmmux streamable=true name=mux\
  jackaudiosrc client-name="stream" do-timestamp=true connect=0 !\
  audioconvert !\
  audiorate !\
  audio/x-raw-float,channels=2,rate=48000,depth=16 !\
  vorbisenc quality=0.5 bitrate=48000 !\
  queue !\
  queue !\
  mux. mux. !\
  queue !\
  shout2send streamname="Kof's TAZ Broadcast" description="live chat: irc.freenode.net @ #kolektiv" genre="livecoding" ip=giss.tv port=8000 password=jwz1m mount=/kof.ogg

