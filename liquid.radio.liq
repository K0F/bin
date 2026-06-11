#!/usr/bin/liquidsoap
# Log dir
set("log.file.path","/tmp/basic-radio.log")

set("jack.client_name","liquidsoap-<pid>")
jack_inp = input.jack(id="RADIO")

 # Stream it out
output.icecast(%vorbis,
  host = "giss.tv", port = 8000,
  password = "jwz1m", mount = "kof.ogg",
  jack_inp)
