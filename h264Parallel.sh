#!/bin/bash
INPUT="$1"
DURATION=$(ffprobe -v error -select_streams v:0 -show_entries stream=duration -of default=noprint_wrappers=1:nokey=1 "$INPUT");
SECS=$(echo $DURATION | awk -F'.' '{print $1}')
FRAG=$(echo $DURATION | awk -F'.' '{print $2}')
NO_OF_SEGMENTS=$(($SECS/60))
echo total duration "$SECS.$FRAG"s
echo number of segments $NO_OF_SEGMENTS
REST=$(( $SECS % 60 )).$FRAG
MINS=0
HOS=0


rm -rf /mnt/central/TEMP_KRYSTOF/parallel/*
echo "" > /tmp/jobs
echo "" > /tmp/files

SCOUNT=0
LOOP_NO=0

while [[ $SCOUNT -le $SECS ]];
do
  TIME=`printf "%02d" $HOS`:`printf "%02d" $MINS`:00
   
  SEGMENT=60
  if [ $LOOP_NO -eq  $NO_OF_SEGMENTS ]
  then
  SEGMENT=$REST
  fi
  
  #echo $TIME $SEGMENT

  OUTPUT=/tmp/$(echo `basename $INPUT` | awk -F'.' '{print $1}')_$TIME.mp4
  
  echo "ffmpeg -loglevel panic -ss $TIME -i $INPUT -t $SEGMENT -c:v h264 -pix_fmt yuv420p -crf 22 -preset ultrafast -threads 1 -c:a aac -y $OUTPUT" >> /tmp/jobs
  echo file $OUTPUT >> /tmp/files
  
  SCOUNT=$(( SCOUNT + 60 ))
  MINS=$(( $MINS + 1 ))
  
  if [ $MINS -ge 59 ]
  then
    MINS=0
    HOS=$(( $HOS + 1 ))
  fi
  LOOP_NO=$(( $LOOP_NO + 1 ))
done

#parallel --eta --progress -S "32/nfaRender,32/nfaDTL01,8/:,8/nfaProjekce,8/nfaAdela" < /tmp/jobs
#parallel --eta --progress -S "8/nfaRender,8/nfaDTL01,4/nfaAdela,8/:,8/nfaProjekce" < /tmp/jobs
#parallel --eta --progress -S "4/nfaRender,4/nfaAdela,4/:,16/nfaProjekce" < /tmp/jobs
parallel --eta --progress -S "4/:" < /tmp/jobs
FIN="$(echo `basename $INPUT` | awk -F'.' '{print $1}')".mp4
ffmpeg -f concat -safe 0 -i /tmp/files -c:v copy -c:a copy -y $FIN
