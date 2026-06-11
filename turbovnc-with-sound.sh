#!/bin/bash
set -e
# Assuming VNC listens on :5911 and you have following in .vnc/xstartup.turbovnc or .profile :
# export PULSE_SERVER=127.0.0.1:4714

if [[ $# -eq 0 ]] ; then
    ANSWER=$(zenity --forms --forms --title="Connect to VNC with sound" --text="Enter credentials" --add-entry="Hostname" --add-entry="Username")
    HN=$(echo $ANSWER | cut -d '|' -f1)
    UN=$(echo $ANSWER | cut -d '|' -f2)
    ARGS="${HN} -l${UN}"
fi

PACTL_MODULE=$(pactl load-module module-native-protocol-tcp auth-ip-acl='::1;127.0.0.1')
ssh -N -L 59011:127.0.0.1:5911 -R 4714:127.0.0.1:4713 ${ARGS} $@ &
vncviewer 127.0.0.1:59011
pactl unload-module $PACTL_MODULE
kill $!
