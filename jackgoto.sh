#!/bin/bash
echo locate $( echo "`tctosec.sh \"$1\"` * 48000" | bc -l ) | jack_transport
