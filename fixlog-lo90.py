#!/usr/bin/python
import sys, getopt, re

# Some defaults
verbose = False

# Initalize some variables
linecount = 0
outfile = ""
outline = 0
lastwrite = ""

ignorelines = []
ignorelines.append("")
ignorelines.append("gr::log :WARN: udp_source0 - Too much data; dropping packet.")
ignorelines.append(">>> Done")

datetimeprevlines = []
datetimeprevlines.append("")
datetimeprevlines.append("***********************************")
datetimeprevlines.append("* MESSAGE DEBUG PRINT PDU VERBOSE *")

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

def contains_datetime(line):
	# Is the line empty?
	if line == "":
		return False
	# It should contain at least two words, a date and a time
	if len(line.split()) < 2:
		return False
	# There should be a date with three components seperated by hyphens
	if len(line.split("-")) < 3:
		return False
	# There should be a time with three components seperated by colons
	if len(line.split(":")) < 3:
		return False
	# There is probably a date/time (the check was kinda lazy...)
	return True

def is_onlydatetime(line):
	# Is the line empty?
	if line == "":
		return False
	# It should contain two words, a date and a time
	words = line.split()
	if len(words) != 2:
		return False
	# The date should have three components seperated by hyphens
	date = words[0].split("-")
	if len(date) != 3:
		return False
	# Make sure each component of the date is an integer
	for item in date:
		if not is_int(item):
			return False
	# The time should have three components seperated by colons
	time = words[1].split(":")
	if len(time) != 3:
		return False
	# Make sure each component of the time is an integer
	for item in time:
		if not is_int(item):
			return False
	# It checks out!
	return True

def is_packetheader(line):
	linematch = re.match(r'^Packet number \d+ \(\w+\)$', line)
	if linematch:
		return True
	else:
		return False
	# # Is the line empty?
	# if line == "":
	# 	return False
	# # It should contain four words
	# words = line.split()
	# if len(words) != 4:
	# 	return False
	# # It should start with 'Packet number'
	# if line[:13] != "Packet number":
	# 	return False
	# # The third word should be an integer
	# if not is_int(words[2]):
	# 	return False
	# # The last word should be encased in parens
	# if words[3][:1] != "(":
	# 	return False
	# if words[3][-1:] != ")":
	# 	return False
	# # It checks out!
	# return True

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

def processfile(logfilename, outputfilename):
	global linecount, lines, outfile, outline
	linecount = 0
	outline = 0
	lines = []
	line = ""
	prevline = ""
	nextline = ""
	relocatequeue = []

	# Open the log file for reading
	logfile = open(logfilename, "r")
	lines = logfile.readlines()
	logfile.close()

	# Open the output file for writing
	outfile = open(outputfilename, "w")

	while linecount < len(lines):
		# Get the previous line (if there is one)
		if linecount > 0:
			prevline = lines[linecount - 1].rstrip("\n")
		# Get the current line
		line = lines[linecount].rstrip("\n")
		# Get the next line (if there is one, otherwise clear nextline)
		if linecount < len(lines) - 1:
			nextline = lines[linecount + 1].rstrip("\n")
		else:
			nextline = ""
		# If the line consists of nothing but a date/time
		if is_onlydatetime(line):
			# And the previous line is nothing but a date/time OR is in the list of valid lines to preceed a date/time
			if is_onlydatetime(prevline) or prevline in datetimeprevlines:
				# Normally placed date/time, write it to the output file
				writeout(line)
			else:
				# The date/time is in the wrong spot
				if is_packetheader(nextline):
					#The packet header was on a line by itself, relocate both
					log("Relocating header for " + nextline + " found at line " + str(linecount + 1))
					relocatequeue.append(line)
					relocatequeue.append(nextline)
					linecount += 1
				else:
					# We have a date/time without a packet header
					log("Relocating date/time without a matching packet header at line " + str(linecount + 1))
					relocatequeue.append(line)
		elif is_packetheader(line):
			# The line is a packet header
			if is_onlydatetime(prevline) or prevline == "***********************************" or prevline == "":
				# Normal packet header, preceeded by a date/time line. Write it to the output file
				writeout(line)
			else:
				# Packet header in the middle of another packet
				if len(relocatequeue) > 0 and is_onlydatetime(relocatequeue[len(relocatequeue) - 1]):
					# We have a date/time waiting to be relocated already, so odds are good this header belongs to the following packet
					relocatequeue.append(line)
					log("Relocating packet header for " + line + " found at line " + str(linecount + 1))
					# If there's a blank line following the packet header, send it along with the header
					if nextline == "":
						relocatequeue.append(nextline)
						linecount += 1
				else:
					# We don't have a date time waiting, who DOES this belong to...
					if is_packetheader(prevline):
						# Two packet headers in a row? Ugly, but we'll leave it be for lack of anything better to do.
						logwarn("Found two packet headers in a row. Leaving unaltered. Headers are:")
						log(" Line " + str(linecount) +  ": " +  prevline)
						log(" Line " + str(linecount + 1) +  ": " +  line)
						writeout(line)
					else:
						# For lack of a better idea, let's move it along...
						logwarn("Relocating packet header for " + line + " found at line " + str(linecount + 1))
						relocatequeue.append(line)
		elif contains_datetime(line):
			# The line contains a date/time but it's mixed in with the data
			# Attempt to extract it with a regex
			linematch = re.match(r'^(.*)?(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})(.*)?$', line)
			if linematch:
				# Success! put the date/time in the relocate queue and write the data (minus the date/time) to the output file
				log("Relocating date/time found mixed in data at line " + str(linecount + 1))
				relocatequeue.append(linematch.group(2))
				writeout(linematch.group(1) + linematch.group(3))
			else:
				# We failed! Write the unmodified line
				logwarn("Line contains an out of place date/time in the data, unable to extract.")
				writeout(line)
		else:
			# Normal line, write it out
			writeout(line)
			# If we found the end of a packet, and there's something in the relocate queue, write the queue to the output file
			if line == "***********************************" and len(relocatequeue):
				#debug("Writing " + str(len(relocatequeue)) + " displaced lines to line " + str(outline + 1) + " of the output file")
				for rq in relocatequeue:
					writeout(rq)
				relocatequeue = []
		# End of the loop, increment the line counter
		linecount += 1

	# Check the relocate queue now that we're done, if there's something in it, write it out
	if len(relocatequeue):
		logwarn(str(relocatequeue) + " lines left in the relocate queue when the end of the file was reached:")
		for rq in relocatequeue:
			writeout(rq)
			print(rq)
		relocatequeue = []
	log("Total lines processed:  " + str(linecount) + "  from  " + logfilename)
	log("Total lines written:    " + str(outline) + "   to   " + outputfilename)
	outfile.close()

def displayusage():
      print 'fixlog-lo90.py --help'
      print 'fixlog-lo90.py --input-file=<inputfile> [--output-file=<outputfile>]'
      print 'fixlog-lo90.py -i <inputfile> -o <outputfile>'

def main(argv):
	global verbose
	inputfile = ""
	outputfile = ""
	try:
		# Any short parameter followed by a colon takes an argument ('i' and 'o' in this case)
		opts, args = getopt.getopt(argv,"hvi:o:",["help", "input-file=","output-file=","verbose"])
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
		elif opt in ("-o", "--output-file"):
			outputfile = arg
		elif opt in ("-v", "--verbose"):
			verbose = True
	if inputfile == "":
		print("Error: You must specify an input file")
		displayusage()
		sys.exit(2)
	if outputfile == "":
		print("Error: You must specify an output file")
		displayusage()
		sys.exit(2)

	debug("Input:  " + inputfile)
	debug("Output: " + outputfile)

	processfile(inputfile, outputfile)

def writeout(line):
	global outfile, outline, lastwrite
	outfile.write(line + "\n")
	outline += 1
	lastwrite = line

def log(output):
	print(output)

def logwarn(output):
	log(str(linecount + 1) + " WARNING: " + output)

def debug(output):
	if verbose:
		log("DEBUG: " + output)

if __name__ == "__main__":
	main(sys.argv[1:])
