#!/bin/bash
if ! command -v sclang >/dev/null 2>&1 || [ ! -f "$HOME/.config/SuperCollider/startup.scd" ]; then
    [ -x "$HOME/bin/setup-sc-node" ] && "$HOME/bin/setup-sc-node"
fi
rm -f /tmp/sclang*
pkill ruby 2>/dev/null || true
pkill sclang 2>/dev/null || true
pkill scsynth 2>/dev/null || true
[ -z "${DISPLAY:-}" ] && [ -z "${WAYLAND_DISPLAY:-}" ] && export QT_QPA_PLATFORM=offscreen
if ! pgrep -x pipewire >/dev/null 2>&1 && ! pgrep -x jackd >/dev/null 2>&1; then
    nohup jackd -r -d alsa -d default -r 48000 -p 1024 -n 3 >/tmp/jackd.log 2>&1 &
    sleep 1
    pgrep -x jackd >/dev/null 2>&1 || nohup jackd -r -d dummy -r 48000 -p 1024 >/tmp/jackd.log 2>&1 &
fi
mkdir -p ~/src/sc/kof/scwork ~/recordings
cd ~/src/sc/kof/
if command -v pw-jack >/dev/null 2>&1 && pgrep -x pipewire >/dev/null 2>&1; then
    exec pw-jack screen scvim `date +%s_%b%d_%a_kof%y`.scd
else
    exec screen scvim `date +%s_%b%d_%a_kof%y`.scd
fi
