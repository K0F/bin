# SAMPLE: FLAC streaming on Windows & Mac
while true
do
  ffmpeg -re -f jack -i stream \
         -ar 48000 \
         -ac 2 \
         -c:a libmp3lame \
         -b:a 192k \
         -f mp3 \
         -content_type 'audio/mpeg' \
         icecast://source:cigareta@xn--peek-h6a.com:9000/radio.mp3
  sleep 1
done
