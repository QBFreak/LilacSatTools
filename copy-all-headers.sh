#!/bin/bash
for i in *.jpg; do
  [ -f "$i" ] || break
  echo
  echo @@ $i
  python copyheader.py --image-file=$i --header-file=$i.hdr || rm $i.hdr
done
