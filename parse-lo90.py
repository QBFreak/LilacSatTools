#!/usr/bin/python
	import sys, getopt

# Some constants
### Header
headerlen = 15
### Footer
footerlen = 8
nextpacketbytes = (0, 2) # Bytes 00-01 (length of 2)

# Some defaults
showpackets = True
showerrors = True
showwarnings = True
verbose = False
outputfilename = ""

# Initalize some variables
foundpacket = False
packettype = ""
packetstart = False
packetnum = 0
nextpacket = ""
packetdata = []	# This may only be used in one place (parseline), but it needs to persist across multiple iterations (lines)
outputfile = ""
imagefilename = ""
imagefile = ""
imagebytes = 0

def is_int(num):
	"Return True if string 'num' is an integer, False otherwise"
	try:
		int(num)
		# Successful type cast
		return True
	except ValueError:
		return False
	# Ack, we shouldn't be here!
	return False

def is_hex(num):
	"Return true if string 'num' is a hexidecimal number, False otherwise"
	try:
		int(num, 16)
		# Successful base conversion
		return True
	except ValueError:
		return False
	# Ack, we shouldn't be here!
	return False

def packeterror(message):
	"Display an error message 'message' and reset the flags to stop processing the current packet"
	global foundpacket, packettype, packetstart
	if showerrors:
		log("** Error in packet " + packetnum + ": " + message)
	packettype = ""
	packetstart = False

def packetwarn(message):
	"Display the warning message 'message' for the current packet"
	if showwarnings:
		log("** Warning for packet " + packetnum + ": " + message)

def extractnext(raw):
	"Return the decimal value of the next packet in sequence, extracted from the raw bytes of the current packet OR return False for invalid packet"
	if len(raw) < headerlen + footerlen:
		# Not enough data, error
		return False
	else:
		extractedbytes = ""
		for i in range(nextpacketbytes[0] + nextpacketbytes[1] - 1, nextpacketbytes[0] - 1, -1):
			extractedbytes += raw[len(raw) + nextpacketbytes[0] + i - footerlen]
		if is_hex(extractedbytes):
			# We return it as a string because we're going to be comparing it to strings. Bad programmer. No cookie.
			return str(int(extractedbytes, 16))
		else:
			# We couldn't convert the value to a number
			return False
	# Ack! We really went wrong because we shouldn't be here
	return False

# Parse a packet into header, body, and footer
def splitpacket(raw):
	"Split a packet and return a tuple of header, body, footer OR return False for invalid packet"
	# Check the length and make sure there's at least a header and a footer
	if len(raw) < headerlen + footerlen:
		# Not enough data, error
		return False
	else:
		# Build the header, body and footer to return
		retheader = []
		retbody = []
		retfooter = []
		for i in range(0, len(raw)):
			if i < headerlen:
				# Header
				retheader.append(raw[i])
			elif i < len(raw) - footerlen:
				# Body
				retbody.append(raw[i])
			else:
				# Footer
				retfooter.append(raw[i])
		# Return the tuple with the parsed packet
		return (retheader, retbody, retfooter)
	# Ack! We shouldn't be here, error
	return False

def getpackettype(line):
	"Returns the packet type from 'line' OR False if none is present"
	# The line should end in )
	if line[-1:] != ")":
		return False
	# The line should contain a single open paren
	if len(line.split("(")) != 2:
		return False
	# The line should contain a single close paren
	if len(line.split(")")) != 2:
		return False
	# Grab the second word split on open paren, and from the result the first word split on close paren
	return line.split("(")[1].split(")")[0]

def parseline(line):
	"Parses 'line' of input from file"
	global foundpacket, packetnum, nextpacket, packettype, packetstart, packetdata

	if line[0:14] == "Packet number " and foundpacket == False:
		foundpacket = True
		packetstart = False
		linedata = []
		packetdata = []
		packetnum = line.split()[2]
		if not is_int(packetnum):
			packeterror("Invalid packet number, not an integer: " + packetnum)
		if packetnum != nextpacket and nextpacket != "":
			packetwarn("Packet out of sequence, expected " + nextpacket)
			nextpacket = ""
		packettype = getpackettype(line)
	elif line == "***********************************":
		if packettype == "camera" and packetstart == False:
			packeterror("Malformed packet! Expected 'contents =' instead found end")
		if packetstart == True:
			parsed = splitpacket(packetdata)
			nextpacket = extractnext(packetdata)
			if parsed != False:
				writebytes(parsed[1])
				if showpackets:
					packetout = "[" + packetnum + "] "
					packetout += "Header: "
					for i in range(0, len(parsed[0])):
						packetout += parsed[0][i] + " "
					packetout += "  Footer: "
					for i in range(0, len(parsed[2])):
						packetout += parsed[2][i] + " "
					packetout += "(next: " + nextpacket + ")"
					log(packetout)
		packettype = ""
		packetstart = False
		foundpacket = False
		packetnum = ""
	elif packettype == "camera":
		if packetstart == False:
			if line == "contents = ":
				packetstart = True
		else:
			linedata = line.split()
			if len(linedata) > 1:
				if linedata[0][-1:] != ":" or is_hex(linedata[0][:4]) == False:
					packeterror("Invalid start of line! Expected offset, found " + linedata[0])
				else:
					if len(line.split("-")) > 1 or len(line.split(":")) > 2:
						packeterror("Header found in data section of packet (2 packets lost)")
					else:
						for i in range(1, len(linedata)):
							if is_hex(linedata[i]):
								packetdata.append(linedata[i])
							else:
								packeterror("Invalid hex value " + linedata[i])
								break
			else:
				packeterror("Data expected but no data found")

def displayusage():
      print 'parse-lo90.py --help'
      print 'parse-lo90.py --input-file=<inputfile> --image-file=<imagefile> [--output-file=<outputfile>] [--supress-packets] [--suppress-warnings] [--suppress-errors]'
      print 'parse-lo90.py -i <inputfile> -m <imagefile> [-o <outputfile>] [-p] [-w] [-e]'

def writebytes(wbytes):
	global imagefile, imagebytes
	for byte in wbytes:
		if is_hex(byte):
			imagefile.write(chr(int(byte,16)))
		else:
			imagefile.write(chr(0))
			log("Warning: Invalid hex value " + byte)
		imagebytes += 1

def log(output):
	print(output)

def debug(output):
	if verbose:
		log("DEBUG: " + output)

def processfile(logfilename):
	global packettype, packetstart, imagefile

	# Open the image file for writing
	imagefile = open(imagefilename, "wb")

	# Open the log file for reading
	logfile = open(logfilename, "r")
	filequeue = []
	misplacedheader = False

	for inline in logfile:
		inline = inline.rstrip("\n")
		if misplacedheader:
			filequeue.append(inline)
			misplacedheader = False
			continue
		if packettype == "camera" and packetstart:
			if len(inline.split()) > 1:
				if len(inline.split()[0].split("-")) == 3 and len(inline.split()[1].split(":")) == 3:
					misplacedheader = True # 22359
		elif not packettype != "camera" and not packetstart:
			for fq in filequeue:
				parseline(fq)
			filequeue = []
		if misplacedheader:
			filequeue.append(inline)
		else:
			parseline(inline)

	logfile.close()
	imagefile.close()
	log(str(imagebytes) + " bytes written to the image file")

def main(argv):
	global inputfile, imagefilename, showpackets, showwarnings, showerrors, verbose
	inputfile = ''
	imagefile = ""
	try:
		# Any short parameter followed by a colon takes an argument ('i' and 'o' in this case)
		opts, args = getopt.getopt(argv,"hpwevi:m:o:",["help", "input-file=","image-file","output-file=","supress-packets","suppress-warnings","suppress-errors","verbose"])
	except getopt.GetoptError:
		print("Error: Invalid command line option")
		displayusage()
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h' or opt == "--help":
			displayusage()
			sys.exit()
		elif opt in ("-i", "--input-file"):
			inputfile = arg
		elif opt in ("-m", "--image-file"):
			imagefilename = arg
	if inputfile == "":
		print("Error: You must specify an input file")
		displayusage()
		sys.exit(2)
	if imagefilename == "":
		print("Error: You must specify an image file")
		displayusage()
		sys.exit(2)

	debug("Input:  " + inputfile)
	debug("Image:  " + imagefilename)
	if outputfilename == "":
		debug("Output: console")
	else:
		debug("Output: " + outputfilename)
	if showpackets == False:
		debug("Suppressing packet data")
	if showwarnings == False:
		debug("Suppressing warnings")
	if showerrors == False:
		debug("Suppressing parsing errors")

	processfile(inputfile)

if __name__ == "__main__":
	main(sys.argv[1:])
