#!/usr/bin/python
"""
copyheader.py - copy the header from a JPEG image to a file
Quick and dirty, this was only throughly tested on a single partial-capture
 image from LO-90 / LilacSat 1
"""

## Function names (almost) made sense at the time
##  by the time you read this, they probably don't

import sys, binascii, argparse

def displayusage():
      print 'copyheader.py --help'
      print 'copyheader.py --image-file=<imagefile>'
      print 'copyheader.py -m <imagefile>'

# To write the header:
#	header = True
# To skip writing it:
#	header = False
header = True

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--image-file', help='input image file', required=True)
if header:
    parser.add_argument('-o', '--header-file', help='output header file', required=True)
args = parser.parse_args()


# Constants
SOI = b'\xFF\xD8'
JFIF = b'\xFF\xE0'
IDENTIFIER = b'\x4A\x46\x49\x46\x00'	# JFIF x00
DQTMARKER = b'\xFF\xDB'
HTMARKER = b'\xFF\xC4'
SOF = b'\xFF\xC0'
SOS = b'\xFF\xDA'
COMMENT = b'\xFF\xFE'
EOI = b'\xFF\xD9'

### Global vars %%%
im = ""
hdr = ""
imagename = args.image_file
headername = args.header_file

### FUNCTIONS ###

# Convert a binary value to integer
def bin2int(data):
	return int(data.encode('hex'), 16)

# Print list of binary values as hex, optionally supress newline
def printhex(data, newline = True):
	for i in range(0, len(data)):
		sys.stdout.write(binascii.b2a_hex(data[i:i+1]) + " ")
	if newline:
		print("")

# Exit the script with an error message, display the offending data if applicable
def fail(message, data):
	print("Error: " + message)
	if data != "":
		sys.stdout.write("Data: ")
		printhex(data)
	sys.exit(1)

# Read len(data) bytes from file and compare to data, display dataname and data
def check(data, dataname):
	b = read(len(data))
	if b == data:
		print("Found " + dataname)
		return
	else:
		fail("Could not find " + dataname, b)

# Look for data at the front of readbuff, display a success message if found
def checkbuffer(data, dataname, buffername):
	if len(data) > len(readbuff):
		fail("Could not find " + dataname + ", not enough data in " + buffername, "")
	else:
            # Retrieve the data from the buffer
            b = readbuffer(len(data))
            if b == data:
                    print("Found " + dataname + " in " + buffername)
                    return
            else:
                    fail("Could not find " + dataname + " in " + buffername, b)

# Return datalen number of bytes from readbuff,
#  remove the returned data from readbuff
def readbuffer(datlen):
	global readbuff
	if len(readbuff) <= datlen:
		# If there's not enough, tough luck, we don't return all of it...
		rb = readbuff
		readbuff = ""
	else:
                # Some goes in rb to be returned, the rest goes back into readbuff
		rb = readbuff[:datlen]
		readbuff = readbuff[datlen:]
	return rb

# Return datalen number of bytes from readbuff if possible,
#  if not enough data in readbuff, read from image file
#  if still processing header, write to header file
def read(datlen):
	global readbuff
	rb = readbuffer(datlen)
	if len(rb) < datlen:
		rb += im.read(datlen - len(rb))
	if header:
		for b in rb:
			hdr.write(b)
	return rb

# Return datlen number of bytes from readbuff, display the data
#  display a conversion of the data to a single integer if 8 or fewer bytes
def readbufferbytes(datlen, dataname):
	sys.stdout.write(dataname + ": ")
	data = readbuffer(datlen)
	if len(data) < datlen:
		fail("Could not read enough data for " + dataname, data)
	printhex(data, False)
	if datlen <= 8:
		print("(" + str(bin2int(data)) + ")")
	else:
		print("")
	return data

# Return datlen number of bytes from the image file, display the data
#  display a conversion of the data to a single integer if 8 or fewer bytes
def readbytes(datlen, dataname):
	sys.stdout.write(dataname + ": ")
	data = read(datlen)
	printhex(data, False)
	if datlen <= 8:
		print("(" + str(bin2int(data)) + ")")
	else:
		print("")
	return data

# Process the file after the JFIF marker
def processjfif():
	global readbuff
	print("Found JFIF Marker")
	jfiflength = readbytes(2, "JFIF Length")
	readbuff = read(bin2int(jfiflength) - 2)
	checkbuffer(IDENTIFIER, "Identifier", "JFIF")
	jfifmaver = readbufferbytes(1, "JFIF Major Version")
	jfifmiver = readbufferbytes(1, "JFIF Minor Version")
	print("JFIF Version: " + str(bin2int(jfifmaver)) + "." + str(bin2int(jfifmiver)))
	xydensunit = readbufferbytes(1, "X/Y Density Units")
	if bin2int(xydensunit) == 0:
		print("X/Y Density Unit is none, X/Y specifies pixel aspect ratio")
	elif bin2int(xydensunit) == 1:
		print("X/Y Density Unit is Dots Per Inch")
	elif bin2int(xydensunit) == 2:
		print("X/Y Density Unit is Dots per Centimeter")
	else:
		fail("Error, invalid X/Y density unit", xydensunit)
	xdens = readbufferbytes(2, "X Density")
	ydens = readbufferbytes(2, "Y Density")
	xthumb = readbufferbytes(1, "X Thumbnail")
	ythumb = readbufferbytes(1, "Y Thumbnail")
	if xthumb != b'\x00':
		fail("Unknown X Thumbnail value", xthumb)
	if ythumb != b'\x00':
		fail("Unknown Y Thumbnail value", ythumb)
	print("No thumbnail")
	if len(readbuff):
		print("Warning: There's more JFIF header here than I know how to process! Discarding remainder:")
		printhex(readbuff)
		readbuff = ""
	return
	## END processjfif()

# Process the file after the Data Quantization Table marker
def processdqt():
	global readbuff, dqt
	print("Found Data Quantization Table marker")
	dqtlength = readbytes(2, "DQT Length")
	readbuff = read(bin2int(dqtlength) - 2)
	while len(readbuff) > 0:
		dqt += 1
		dqtprecision = readbufferbytes(1, "DQT [" + str(dqt) + "] Precision")
		if bin2int(dqtprecision) == 0:
			print("DQT Precision is 8-bit")
		elif bin2int(dqtprecision) == 1:
			print("DQT Precision is up to 16-bit")
		else:
			fail("Unknown DQT Precision", dqtprecision)
		dqtvalues = readbufferbytes(64, "DQT Values")
	return
	## END processdqt()

# Process the file after the Huffman Table marker
def processht():
	global readbuff, ht
	print("Found Huffman Table Marker")
	htlength = readbytes(2, "HT Length")
	readbuff = read(bin2int(htlength) - 2)
	while len(readbuff) > 0:
		ht += 1
		htindex = readbufferbytes(1, "HT [" + str(ht) + "] Index")
		if bin2int(htindex) > 15:
			print("AC Table")
		else:
			print("DC Table")
		htbits = readbufferbytes(16, "HT Bits")
		htremlen = 0
		for htbit in htbits:
			htremlen += bin2int(htbit)
		print("Huffman Values byte count: " + str(htremlen))
		htvals = readbufferbytes(htremlen, "Huffman Values")
	return
	## END processht()

# Process the file after the Frame marker
def processframe():
	global readbuff, frame
	print("Found Frame Marker")
	framelength = readbytes(2, "Frame Length")
	readbuff = read(bin2int(framelength) - 2)
	while len(readbuff) > 0:
		frame += 1
		precision = readbufferbytes(1, "Sample Precision [" + str(frame) + "]")
		y = readbufferbytes(2, "Y")
		x = readbufferbytes(2, "X")
		numcomp = readbufferbytes(1, "Number of components")
		if bin2int(numcomp) == 1:
			if frame == 1:
				print("Grayscale JPEG Image")
		elif bin2int(numcomp) == 3:
			if frame == 1:
				print("Color JPEG Image")
		else:
			fail("Unknown JPEG color type!", numcomp)
		for i in range(0, bin2int(numcomp)):
			compid = readbufferbytes(1, "Component ID")
			hvsamp = readbufferbytes(1, "H/V Sampling Factors")
			qtnum = readbufferbytes(1, "QT Number")
	return
	## END processframe()

# Process the file after the Scan marker,
### Assume end of header when complete
def processscan():
	global readbuff, header
	print("Found Scan Marker")
	scanlength = readbytes(2, "Scan Length")
	readbuff = read(bin2int(scanlength) - 2)
	numcomp = readbufferbytes(1, "Number of components")
	for i in range(0, bin2int(numcomp)):
		compid = readbufferbytes(1, "Component ID")
		dcactable = readbufferbytes(1, "DC and AC table numbers")
	ss = readbufferbytes(1, "Ss")
	se = readbufferbytes(1, "Se")
	ahai = readbufferbytes(1, "Ah and Ai")
	if len(readbuff) > 0:
		fail("Unknown data remaining in Scan Marker", readbuff)
	header = False
	return
	## END processscan()

# Process the file after the Comment marker
### UNIMPLIMENTED ###
def processcomment():
	global readbuff
	print("Found Comment Marker")
	fail("DON'T KNOW HOW TO PROCESS COMMENTS YET!", "")
	return
	## END processcomment()

# Process the file after the End of Image marker
### UNTESTED ###
### Is this how it's actually supposed to behave?
### I kinda assumed that it was supposed to make up the last bytes in the file,
###  thus my read() below should come up empty (EOF). My test image was corrupted
def processeoi():
	global readbuff
	print("Found End of Image Marker")
	readbuff = read(16)
	if len(readbuff) > 0:
		fail("Data in file past End of Image Marker")
	return
	## END processeoi()

### BEGIN PROGRAM ###
inputfile = ''
imagefile=""

# Initialize globals
readbuff = ""
dqt = 0
ht = 0
frame = 0

# Open files
im = open(imagename, "rb")
if header:
	hdr = open(headername, "wb")

# The very first thing is the Start of Image
check(SOI, "SOI")

# Look for markers
while True:
	marker = read(2)
	if header:
		if marker == JFIF:
			processjfif()
		elif marker == DQTMARKER:
			processdqt()
		elif marker == HTMARKER:
			processht()
		elif marker == SOF:
			processframe()
		elif marker == SOS:
			processscan()
		elif marker == COMMENT:
			processcomment()
		else:
			fail("Unknown marker", marker)
	elif marker == EOI:
		processeoi()
	elif marker == "":
		print("No more data in file")
		break

if type(im) != type(str()):
	im.close()
if type(hdr) != type(str()):
	hdr.close()
