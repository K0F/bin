#!/bin/bash
echo "creating /tmp/fifo file pass some byte to shout out loud"
mkfifo /tmp/fifo
while true; do cat /tmp/fifo | broadcastShout 10000; done
