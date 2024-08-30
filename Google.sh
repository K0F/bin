#!/bin/sh
a='google.com/search?q='
c=$a$1
echo searching!
echo $c
elinks -dump --no-numbering --no-references $c | sed -n '/[0-9]\./,+2p'
