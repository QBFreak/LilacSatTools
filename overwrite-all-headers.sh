#!/bin/bash
for i in *.jpg; do
  [ -f "$i" ] || break
  echo
  echo @@ $i
  python overwriteheader.py --header-file=GOOD.hdr --image-file=$i --output-file=$i.new.jpg
done
