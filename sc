#!/bin/bash
rm /tmp/sclang*
pkill ruby
pkill sclang
pkill scsynth
cd ~/src/sc/kof/
#touch `date +%s_%b%d_%a_kof%y`.scd
#git add `date +%s_%b%d_%a_kof%y`.scd
screen scvim `date +%s_%b%d_%a_kof%y`.scd
