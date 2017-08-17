#!/usr/bin/python
"""
overwriteheader.py - copy a saved header from a JPEG image to a file
Quick and dirty, it just overwrites len(header) bytes of the target file with
 the specified header.
"""
import sys, binascii, argparse

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--header-file', help='input header file', required=True)
parser.add_argument('-m', '--image-file', help='input image file', required=True)
parser.add_argument('-o', '--output-file', help='output image file', required=True)
args = parser.parse_args()

### Global vars %%%
im = ""
hdr = ""
imagename = args.image_file
headername = args.header_file
outputname = args.output_file

### BEGIN PROGRAM ###
inputfile = ''
imagefile = ''
outputfile = ''

# Open files
hdr = open(headername, "rb")
im = open(imagename, "rb")
out = open(outputname, "wb")

header = True
while True:
    rb = im.read(1)
    imrb = rb
    if header:
        rb = hdr.read(1)
        if rb == "":
            rb = imrb
            header = False
    if rb == "":
        break
    else:
        out.write(rb)

hdr.close()
im.close()
out.close()
