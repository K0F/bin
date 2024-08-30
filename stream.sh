# SAMPLE: FLAC streaming on Windows & Mac
while true
do
  ffmpeg -f jack -i stream \
         -ar 48000 \
         -ac 2 \
         -c:a opus \
		 -fflags +igndts \
         -f ogg \
         -strict -2 \
         -content_type 'application/ogg' \
         icecast://source:cigareta@pesek.ddns.net:8000/stream.ogg
  sleep 1
done
