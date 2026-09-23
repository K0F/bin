#!/bin/bash
ffmpeg -f pulse -i default.monitor -c:a libmp3lame -b:a 192k -f mp3 pipe:1 | python3 -c '
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("192.168.1.101", 9000))
s.sendall(b"SOURCE /radio.mp3 HTTP/1.0\r\nAuthorization: Basic c291cmNlOmNpZ2FyZXRh\r\nContent-Type: audio/mpeg\r\n\r\n")

s.settimeout(2.0)
try:
    resp = s.recv(1024)
    print("Icecast:", resp.decode(errors="ignore"), file=sys.stderr)
except Exception:
    pass
s.settimeout(None)

while True:
    data = sys.stdin.buffer.read(4096)
    if not data:
        break
    try:
        s.sendall(data)
    except socket.error:
        break
s.close()
'
