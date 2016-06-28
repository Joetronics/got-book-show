"""
Game of Thrones chapters vs episodes chart generator
Copyright (c) 2013-2016, Joel Geddert

This script generates an HTML file of the table.

Software License:
	This program is free software: you can redistribute it and/or modify
	it under the terms of the GNU General Public License as published by
	the Free Software Foundation, either version 3 of the License, or
	(at your option) any later version.

	This program is distributed in the hope that it will be useful,
	but WITHOUT ANY WARRANTY; without even the implied warranty of
	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
	GNU General Public License for more details.

	You should have received a copy of the GNU General Public License
	along with this program.  If not, see <http://www.gnu.org/licenses/>.

A note from the author:
	The original chart generated by this code, as well as all remaining applicable
	source & asset files (except where noted), are licensed under a Creative Commons
	BY-SA 4.0 license <http://creativecommons.org/licenses/by-sa/4.0/>. If you are
	going to use any of this code to create a derivative work, please respect this
	CC license.
"""

_copyrightInfo = "(c) 2013-2016 Joel Geddert"

##### Imports #####

import re
import csv
import string
from os.path import join
import gzip

##### Hard-coded variables and other runtime parameters #####

_debug = False
_useImgHeaders = True

_hideShowSpoilersFromChapNames = False # Doesn't fully work!
_getSeasonOfChap = False # Doesn't fully work!

_currSeason = 5
_latestEpisode = 50

_htmlTemplateFilenameInter = join('input', 'template.html')
_htmlTemplateFilenamePrint = join('input', 'template-print.html')
_outputFilenameInter = join('output', 'bookshow.html')
_outputFilenamePrint = join('output-print', 'bookshow_print.html')
_tableLine = '<!--table-->'

_chapterFilename = join('input', 'chapters.csv')
_combinedFilename = join('input', 'combined.txt')
_episodeFilename = join('input', 'episodes.csv')
_connectionsFilename = join('input', 'connections.csv')

_filesToGzip = [_outputFilenameInter]
#_filesToGzip = [_outputFilenameInter, join('output','js','got.js'), join('output','css','bookshow.css')]

# abbreviated book names
_bookAbbrevs = ['AGoT','ACoK','ASoS','AFfC','ADwD','TWoW','ADoS']

# If chapter name is longer than this many characters, it will be abbreviated
# (Based on number of characters the stringLen function below will return, which is approximate)
_maxChapNameLength = 15

# Darken every n cells
_nStripe = 5

# HTML indentation character - ASCII tab "\t", several spaces, or nothing.
_tab="\t"

# Windows EOL (\r\n)
_eol="\r\n"

_topLeftBox = '<img src=\"imgs/cornerbox.png\">'
#_topLeftBox = '&nbsp;'

##### Functions #####

# No numpy necessary!
def cumsum(x):
	return [sum(x[:i+1]) for i in range(len(x))]

# macro to output a line
def opl(line):
	# global vars g_opInterVer and g_opPrintVer are switches to turning printing to interactive version and print version on or off
	global g_opPrintVer, g_opInterVer
	global g_outFileInter, g_outFilePrint, _eol
	
	if g_opInterVer:
		g_outFileInter.write(line + _eol)
	if g_opPrintVer:
		g_outFilePrint.write(line + _eol)

# output, without eol
def op(line):
	global g_opPrintVer, g_opInterVer
	global g_outFileInter, g_outFilePrint, _eol
	if g_opInterVer:
		g_outFileInter.write(line)
	if g_opPrintVer:
		g_outFilePrint.write(line)

# Not the best way of doing this, but it's only used for season numbers so it probably only ever needs to support 1-10
def toRomanNumeral(num):
	romnums = ['I','II','III','IV','V','VI','VII','VIII','IX','X']
	if (num < 1) or (num > len(romnums)):
		# Fallback in case the show is more than 10 seasons and I forget to update the code yet
		print("WARNING: roman numeral out of bounds")
		return num
	else:
		return romnums[num-1]

# Approximation for string length
# This isn't going to be perfect because that requires not only rendering the text, but doing it
# in exactly the font (and kerning) the browser will use
# These method should be close enough
def stringLen(s):
	n = 0
	# Iterate 1 character at a time
	for c in s:
		if c in '.\'':
			n += 0.33
		elif c in ' iIl':
			n += 0.5
		elif c in 'ACDGmw':
			n += 1.25
		elif c in 'MOQW':
			n += 1.5
		elif c in string.ascii_lowercase + string.ascii_uppercase + string.digits + '?':
			n += 1
		else:
			print('WARNING: unknown char ' + c + ' in string ' + s)
			n += 1

	return n

# Prefix is something we want to prepend to string, that will always be prepended in full
# and won't count toward checking if string is just 'the' or blank
# (i.e. prepending book abbreviation or number to chapter name)
def abbrevString(s, nChar, prefix=''):
	
	bAddPrefix = (prefix != '')
	
	if bAddPrefix:
		prefix = prefix + ' '
		# Make room in character limit for prefix
		nChar -= stringLen(prefix)

	# Check if we even need to abbreviate at all
	if stringLen(s) <= nChar:
		if bAddPrefix:
			return prefix + s
		else:
			return s

	# Once we reach this point, we know we need to abbreviate.
	# Make room in character limit for however many characters ellipsis will take
	nChar -= stringLen('...')

	# Try taking as many whole words as we can fit
	ss = s.split()
	nwords = len(ss)
	outstr = ''
	for n in range(nwords):
		if stringLen(' '.join(ss[0:n])) < nChar:
			outstr = ' '.join(ss[0:n])
		else:
			break

	# Now check if this ended up abbreviating to blank or just 'the'
	# If so, instead take as many characters as possible
	if (outstr == '') or (outstr.lower() == 'the'):
		outstr = ''
		for c in s:
			if stringLen(outstr + c) >= nChar:
				break
			outstr += c
	
	# If it ended on an apostrophe, remove it
	if outstr[-1:] == '\'':
		outstr = outstr[:-1]

	if bAddPrefix:
		outstr = prefix + outstr

	outstr += '...'

	if _debug:
		print("Abbreviating chapter '" + prefix + s + "' as '" + outstr + "'")

	return outstr

def findChapter(chapName,bookNum):
	global g_chapterList
	global g_bookNChap
	
	chapter = [item for item in g_chapterList if (item['bookNum'] == bookNum) and (item['name'] == chapName)]

	if len(chapter) == 0:
		return {}

	if len(chapter) > 1:
		print("WARNING: multiple chapters found matching book #", bookNum, "named", chapName)

	return chapter[0]

	# If wanting to return total chapter number instead
	# The 1 is because chapters are zero-indexed in csv file (though probably want to change this later)
	#return int(chapter[0]['number']) + 1 + sum(g_bookNChap[0:bookNum-1])


def findChapterByNumber(bookNum,chapNum):
	global g_chapterList
	global g_bookNChap
	
	chapter = [item for item in g_chapterList if (item['bookNum'] == bookNum) and (item['chapNum'] == chapNum)]

	if len(chapter) == 0:
		return {}

	if len(chapter) > 1:
		print("WARNING: multiple chapters found matching book #", bookNum,  " chap#", chapNum, sep="")

	return chapter[0]

def isChapNameEmpty(chapName):
	x = ''.join(ch for ch in chapName if ch.isalnum())
	return (x == '')

#FIXME: this assumes always 10 episodes per season!
def getSeasonNumForEpNum(epNum):
	return ((epNum - 1) // 10) + 1

def getAllChaptersWithPov(pov):
	chaps = [item for item in g_chapterList if item['pov'] == pov]
	chaps = sorted(chaps, key=lambda k: k['totChapNum'])
	return chaps

# Unused, and doesn't work 100% (can enable with _getSeasonOfChap = True)
# This whole function is probably a bad idea, as this is somewhat subjective and should
# probably just be manually set like the connections themselves
# In any case, hiding spoilers by season isn't implemented anyway, so this won't do anything useful
def getSeasonNumForChapter(chapter, strongConnsOnly=False):

	# Criteria:
	# 1. If chapter name is empty (e.g. unreleased chapters that show '?'), return 0
	# 2. If there is a strong connection, use 1st season the connection occurs in
	# 3. If "occurred" flag isn't set, return 0
	# 4. If there's a weak connection, return one of those (currently first, but that may need to change)
	# 5. Find next POV chapter of that character with a strong connection and use that one

	if isChapNameEmpty(chapter['name']):
		return 0
	
	# Make list of all connections that match this chapter
	conns = [item for item in g_connList if item['totChapNum'] == chapter['totChapNum']]
	conns = sorted(conns, key=lambda k: k['epNum'])
	
	if strongConnsOnly:
		strongconns = [item for item in conns if item['strength'] > 0]
		
		if strongconns != []:
			return getSeasonNumForEpNum(strongconns[0]['epNum'])
	
	if chapter['occurred'] == '0':
		return 0

	if not strongConnsOnly:	
		if conns != []:
			return getSeasonNumForEpNum(conns[0]['epNum'])

	# Find next POV chapter of this character and use that chapter's number (recursively)
	chaps = getAllChaptersWithPov(chapter['pov'])
	idx = chaps.index(chapter)
	if (idx + 1) < len(chaps):
		nextPovChap = chaps[idx+1]
		# TODO: change this to strongConnsOnly=True (but make that actually work)
		return getSeasonNumForChapter(nextPovChap, strongConnsOnly=False)

	# No connection was found
	print('WARNING: Book', chapter['bookNum'], 'Chapter', chapter['name'], 'has no strong connections but has occurred flag set')
	return 0
	
##### Main parsing functions #####

def parseChapters():
	print("Processing", _chapterFilename)
	chapterList = []
	bookList = []
	bookNChap = []
	totChapNum = 0
	with open(_chapterFilename) as csvFile:
		chapterfile = csv.reader(csvFile)
		bookname = ""
		bookNum = 0
		for row in chapterfile:
			prevbookname = bookname
			bookname = row[0]
			if bookname != "":
				chapNum  = int(row[1])
				chapName = row[2]
				povchar  = row[3]
				if povchar == '':
					# if no POV char given in CSV file, use first word of chapter name
					povchar = row[2].split()[0]
					if povchar[0:3].lower() in ["pro","epi"]:
						# If it's a prologue/epilogue then always make it "other"
						povchar = "Other"
					elif povchar[0:3].lower() == "the":
						# IF it's a "the" chapter, there should be a pov char set!
						print("WARNING: no POV char given for chapter " + chapName)
						povchar = "Other"
				location  = row[4]
				storyline = [row[5].lower()]
				if (row[6] != ""):
					storyline.append(row[6].lower())
				occurred  = row[7]
				if bookname not in bookList:
					bookList.append(bookname)
					bookNum += 1
					bookNChap.append(1)
				else:
					bookNChap[bookNum-1] += 1
				
				totChapNum += 1

				chapter = {	'book':bookname,
							'bookNum':bookNum,
							'number':chapNum,
							'totChapNum':totChapNum,
							'name':chapName,
							'pov':povchar,
							'story':storyline,
							'location':location,
							'occurred':occurred}
							
				chapterList.append(chapter)
	if _debug:
		print(repr(chapterList[0:10]))

	return chapterList, bookList, bookNChap

def parseCombinedOrder():
	print("Processing", _combinedFilename)
	combinedChapterList = []
	with open(_combinedFilename, 'rU') as txtFile:
		line = txtFile.readline()
		while line:

			words = line.split()
			words = [word.lower() for word in words]

			bookNum = 0
			
			if 'affc' in words:
				bookNum = 4
				n = words.index('affc')
			elif 'adwd' in words:
				bookNum = 5
				n = words.index('adwd')
			else:
				print("ERROR: neither AFFC nor ADWD not found in line:")
				print(line)
				line = txtFile.readline()
				continue

			# combined.txt 1-indexes chapters
			chapNum = int(words[n+1]) - 1

			chapter = g_chapterList[chapNum + g_bookChapOffset[bookNum-1]]
			combinedChapterList.append(chapter)

			if _debug:
				print(chapter)
				print(repr(combinedchapter))
				print(line)

			line = txtFile.readline()
	return combinedChapterList

def parseEpisodes():
	print("Processing", _episodeFilename)
	episodeList = []
	with open(_episodeFilename) as csvFile:
		episodeFile = csv.reader(csvFile)
		for row in episodeFile:
			season = row[0]
			if season != "":
				epname = row[3]
				epname = epname[1:-1]
				if _debug:
					print(epname)
				episode = {'season': season, 'name': epname}
				episodeList.append(episode)
	return episodeList

def parseConnections():
	print("Processing", _connectionsFilename)
	connList = []
	with open(_connectionsFilename) as csvFile:
		connectionfile = csv.reader(csvFile)
		for row in connectionfile:
			if row[0].isdigit():
				epNum = int(row[1]) + 10*(int(row[0])-1)
				bookNum = int(row[2])
				chapName = row[3]
				strength = row[4]
				major = row[5]
				notes = row[6]

				if (chapName == '') or (chapName == '?'):
					continue

				if strength not in ['0','1']:
					print("WARNING: chapter strength not 0 or 1")
					print(_tab, "book ", bookNum,  " chapName ", chapName, sep="")
					print(_tab, "strength: ", strength, sep="")
					continue
				strength = int(strength)
					
				# Make sure chapter name is in the list of chapters!
				chapter = findChapter(chapName,bookNum)
				
				if (chapter == {}):
					print("WARNING: Chapter not found:")
					print(_tab, "book ", bookNum, " chapName ", chapName, sep="")
					print(_tab, "notes: ", notes, sep="")

				# This line causes it to crash when the chapter is incorrectly named (which is okay!)
				chapNum = int(chapter['number']) + 1 + sum(g_bookNChap[0:bookNum-1])
				
				if _debug:
					print("chapName:", chapName, "chapNum:", chapNum)

				connection = {	'epNum':epNum,
								'bookNum':bookNum,
								'chapName':chapName,
								'totChapNum':chapNum,
								'strength':strength,
								'major':major,
								'notes':notes}
								
				connList.append(connection)

	if _debug:
		print(repr(connList[0:10]))

	return connList

##### Main printing functions #####

def printHtmlHeader():
	global g_opInterVer, g_opPrintVer
	print("Writing HTML header")
	
	g_opInterVer = True
	g_opPrintVer = False
	line = ''
	while _tableLine not in line:	
		line = g_inFileInter.readline()

		if not line.endswith('\n'):
			print("ERROR: line", _tableLine, "not found!")
			exit()

		op(line)

	g_opInterVer = False
	g_opPrintVer = True
	line = ''
	while _tableLine not in line:	
		line = g_inFilePrint.readline()

		if not line.endswith('\n'):
			print("ERROR: line", _tableLine, "not found!")
			exit()

		op(line)

	g_opInterVer = True
	g_opPrintVer = True

def printHtmlFooter():
	global g_opInterVer, g_opPrintVer
	print("Writing HTML footer")

	g_opInterVer = True
	g_opPrintVer = False
	while True:
		line = g_inFileInter.readline()
		if not line.endswith('\n'):
			break;
		op(line)
	
	g_opInterVer = False
	g_opPrintVer = True		
	while True:
		line = g_inFilePrint.readline()
		if not line.endswith('\n'):
			break;
		op(line)

	g_opInterVer = True
	g_opPrintVer = True
	

def printBookTitleCells():
	for n in range(len(g_bookList)):
		
		# Column that summarizes book (for when column set is collapsed)
		classes = "booktitle b"+str(n+1)+"title b"+str(n+1)+"c"
		op(_tab + "<th rowspan=\"2\" class=\""+classes+"\" onclick=\"expandbook("+str(n+1)+")\">")
		
		if _useImgHeaders:
			opl("<img src=\"imgs/b" + str(n+1) + "coll.png\" alt=\"" + g_bookList[n] + "\">")
		else:
			op("<div class=\"booktitleabbrevrotate\"><div class=\"booktitleabbrevinside\">")
			op(_bookAbbrevs[n])
			op("</div></div>")
		
		opl("</th>")
		
		classes = "booktitle b"+str(n+1)+"title b"+str(n+1)
		op(_tab + "<th colspan=\""+str(g_bookNChap[n])+"\" class=\""+classes+"\" onclick=\"collapsebook("+str(n+1)+")\">")
		
		if _useImgHeaders:
			opl("<img src=\"imgs/b" + str(n+1) + "title.png\" alt=\"" + g_bookList[n] + "\">")
		else:
			op(g_bookList[n])
		opl("</th>")

		if (n == 4):
			# Print combined order

			# Use 45 as bookNum for css (as much as I like the series, I hope it never hits 45 books...)
			classes = "booktitle b45title b45c"
			op(_tab + "<th rowspan=\"2\" class=\""+classes+"\" onclick=\"expandbook(45)\">")
			
			if _useImgHeaders:
				opl("<img src=\"imgs/b45coll.png\" alt=\"" + g_bookList[3] + " &amp; " + g_bookList[4] + " (Chronological)\">")
			else:
				op("<div class=\"booktitleabbrevrotate\"><div class=\"booktitleabbrevinside\">")
				op("4+5")
				op("</div></div>")
			
			opl("</th>")
			
			classes = "booktitle b45title b45"
			op(_tab + "<th colspan=\""+str(g_bookNChap[3]+g_bookNChap[4])+"\" class=\""+classes+"\" onclick=\"collapsebook(45)\">")
			
			if _useImgHeaders:
				op("<img src=\"imgs/b45title.png\" alt=\"" + g_bookList[3] + " &amp; " + g_bookList[4] + " (Chronological)\">")
			else:
				op(g_bookList[3]+" &amp; "+g_bookList[4]+" (Chronological)")
			
			opl("</th>")

def printChapterTitleCells():
	n = 0
	combinedsection = 0
	prevchapbooknum = -1
	prevchapnum = -1

	for chap in g_interleavedChapterList:
		
		bookNum = int(chap['bookNum'])
		chapNum = int(chap['number'])

		# Determine if chapter is new book

		# if gone down in book number or chapter number
		if (bookNum <= prevchapbooknum):
			if (chapNum <= prevchapnum):
				if not combinedsection:
					n = 0
				combinedsection = 1

				if _debug:
					print("bookNum=", bookNum, " chapNum=", chapNum, sep="")

		elif bookNum == 6:
			combinedsection = 0

		if (bookNum != prevchapbooknum and not combinedsection):
			if _debug:
				print("bookNum=", bookNum, " prevchapbooknum=", prevchapbooknum, " combinedsection=", combinedsection, sep="")
			n = 0
			
		chapName = chap['name']

		# For "?" chapters after TWOW preview chaps
		chapNameIsntReal = isChapNameEmpty(chapName)
		
		# if name longer than ~15 characters, abbreviate
		if combinedsection:
			# If we're in combined section, prepend book number to chapter
			chapName = abbrevString(chapName, _maxChapNameLength, str(bookNum))
		else:
			chapName = abbrevString(chapName, _maxChapNameLength)

		if chapNameIsntReal:
			classes = "cn b" + str(chap['bookNum']) + " bb"

			if (chap['number'] == 0):
				classes += " lb"
			elif (n == g_bookNChap[int(chap['bookNum'])-1]-1):
				classes += " rb"

		elif combinedsection:
			classes = "cn b45 b" + str(bookNum) + "co bb"

			if (n == 0):
				classes += " lb"
			elif (chapNum == (g_bookNChap[4]-1)):
				classes += " rb"

		else:
			classes = "cn b" + str(chap['bookNum']) + " bb"
			
			if (chap['number'] == 0):
				classes += " lb"
			elif (n == g_bookNChap[int(chap['bookNum'])-1]-1):
				classes += " rb"
			
		if n % _nStripe == 0:
			classes += " s"

		if chapNameIsntReal:
			opl(_tab + "<th class=\""+classes+"\"><div class=\"cni nonrotate\">?</div></th>")

		else:
			classes2 = "cni"

			if _getSeasonOfChap:
				# Get episode number that corresponds to this chapter (used for hiding show spoilers)
				chapSeason = getSeasonNumForChapter(chap)

				if _debug:
					print('Chapter', chap['totChapNum'], 'chapSeason', chapSeason)

				if chapSeason == 0:
					classes2 += " ho"
				elif _hideShowSpoilersFromChapNames:
					classes2 += " seas" + str(chapSeason)
			
			elif chap['occurred'] == '0':
				classes2 += " ho"

			opl(_tab + "<th class=\""+classes+"\" title=\""+chap['name']+"\"><div class=\"cnr\"><div class=\""+classes2+"\">"+chapName+"</div></div></th>")
		n += 1

		prevchapbooknum = bookNum
		prevchapnum = chapNum

def printBodyCells(seasEpNum, totEpNum):

	# First, make list of all connections that match this episode
	conns = [item for item in g_connList if item['epNum'] == totEpNum]

	connums = [item['totChapNum'] for item in conns]

	if _debug:
		print("episode ", totEpNum, ", ", len(conns), " connections: ", repr(connums), sep="")
		if _debug:
			print(repr(conns), _eol)

	prevbooknum = -1
	prevchapnum = -1
	combined45section = 0
	totChapNum = 1

	debugprintthisline = (totEpNum == 1)

	for chapter in g_interleavedChapterList:

		isnewbook = 0

		bookNum = int(chapter['bookNum'])
		chapNum = int(chapter['number'])

		totChapNum = chapter['totChapNum']

		# Determine if chapter is new book

		# if gone down in both book number and chapter number, we're in 4+5 combined section
		if (bookNum <= prevbooknum):
			if (chapNum <= prevchapnum):
				if not combined45section:
					isnewbook = 1
				combined45section = 1
		elif bookNum == 6:
			combined45section = 0

		if ((bookNum != prevbooknum) and not combined45section):				
			isnewbook = 1

		if _debug and debugprintthisline:
			if newbook:
				if not combined45section:
					print('')
					print('Book', bookNum, 'start')
				else:
					print('')
					print('Book 4+5 combined start')

		prevbooknum = bookNum
		prevchapnum = chapNum


		if isnewbook:
			n = 0

			# Add book summary cell

			if not combined45section:
				classes = "b" + str(bookNum) + "c lb rb"
			else:
				classes = "b45c lb rb"

			if seasEpNum == 1:
				classes += " tb"
			elif (seasEpNum == 10):
				classes += " bb"
			if (seasEpNum-1) % _nStripe == 0:
				classes += " s"
				
			op(_tab + "<td class=\""+classes+"\">")

			# Get all connections matching this episode
			if not combined45section:
				epbookconns = [item for item in conns if ((item['epNum'] == totEpNum) and (item['bookNum'] == bookNum))]
			else:
				epbookconns = [item for item in conns if ((item['epNum'] == totEpNum) and (item['bookNum'] in [4, 5]))]
				

			# Is there a connection? If so, make div inside cell
			if epbookconns != []:

				classes = "c"

				# Now figure out if there are strong connections or only weak

				strongepbookconns = [item for item in epbookconns if item['strength'] == 1]
				
				if strongepbookconns == []:
					classes += " wc"
				else:
					classes += " sc"

				op("<div class=\"" + classes + "\"></div>")


			opl("</td>")				

		# Print cell

		if _debug and debugprintthisline:
			print("Book", bookNum, "Chapter", chapNum)

		if not combined45section:
			classes = "b" + str(bookNum)
		else:
			classes = "b45 b" + str(bookNum) + "co"

		if (seasEpNum == 1):
			classes += " tb"
		if (seasEpNum == 10):
			classes += " bb"

		if not combined45section:
			if (chapNum == 0):
				classes += "  lb"
			if (chapNum == g_bookNChap[bookNum-1]-1):
				classes += " rb"
		else:
			if (bookNum == 4 and chapNum == 0):
				classes += " lb"
			if (bookNum == 5 and chapNum == (g_bookNChap[4]-1)):
				classes += " rb"

		if (n % _nStripe == 0) or ((seasEpNum-1) % _nStripe == 0):
			classes += " s"

		if _debug and debugprintthisline:
			if 'lb' in classes:
				print('left border')
			if 'rb' in classes:
				print('right border')

		op("<td class=\"" + classes + "\">")

		# Is there a connection? If so, make div inside cell
		if totChapNum in connums:
			conn = [item for item in conns if item['totChapNum'] == totChapNum][0]

			chap = g_chapterList[totChapNum-1]
			povchar  = chap['pov'].lower()
			location = chap['location'].lower()


			classes = "c pov" + povchar

			if False:
				# None of these are implemented in html/js/css anyway, so there's no point to doing them

				classes += " loc" + location

				# TODO: multiple storylines
				storyline = chap['story'][0]
				if storyline != "":
					classes += " sto" + storyline
			
			if conn['strength'] == 0:
				classes += " wc"
			else:
				classes += " sc"

			title = re.sub('"', '&quot;', conn['notes'])
			
			op("<div class=\"" + classes + "\" title=\"" + title + "\"></div>")
		
		op("</td>")
		n += 1

# isBody indicates if this is the one that goes inside the main table
# isEnd indicates if this is the one that goes at the very end (for print version)
def printEpisodeRows(isBody, isEnd=False):
	prevseason = ''
	seasEpNum = 0
	totEpNum = 0

	hideOnFloat = ''
	if isBody:
		hideOnFloat = ' hideonfloat'
	for episode in g_episodeList:

		totEpNum += 1

		if (seasEpNum % _nStripe == 0):
			stripe = ' s'
		else:
			stripe = ''

		seasonclass = "seas" + episode['season']

		seasontitleclass = seasonclass + "title"

		if int(episode['season']) == _currSeason:
			if totEpNum <= _latestEpisode:
				seasonclass += "aired"
			else:
				seasonclass += "unaired"

		if episode['season'] != prevseason:
			opl("<tr class=\"eprow epkeyrow " + seasonclass+ "\">")
			prevseason = episode['season']
			seasEpNum = 1
		else:
			opl("<tr class=\"eprow " + seasonclass + "\">")
			seasEpNum += 1

		classes = stripe
		if (seasEpNum == 1):
			classes += " tb"
		elif (seasEpNum == 10):
			classes += " bb"

		if isEnd:
			op(_tab + "<th class=\"eptitle lb" + classes + hideOnFloat + "\">")
			op("<div class=\"eptitleinside\">")
			opl(episode['name'] + "</div></th>")
			opl(_tab + "<th class=\"epnum" + classes + hideOnFloat + " rb\">" + str(seasEpNum) + "</th>")

		if seasEpNum == 1:
			opl(_tab + "<th rowspan=\"10\" class=\"seasontitle " + seasontitleclass + hideOnFloat + "\">")
			
			if _useImgHeaders:
				opl("<img src=\"imgs/s" + str(episode['season']) + "title.png\" alt=\"Season " + str(episode['season']) + "\">")
			else:
				opl(_tab + _tab + "<div class=\"seasonnamerotate\">")
				opl(_tab + _tab + _tab + "<div class=\"seasonnameinside\">Season "+ toRomanNumeral(int(episode['season'])) + "</div>")
				opl(_tab + _tab + "</div>")

			opl(_tab + "</th>")

		if not isEnd:
			opl(_tab + "<th class=\"epnum" + classes + hideOnFloat + "\">" + str(seasEpNum) + "</th>")
			op(_tab + "<th class=\"eptitle rb" + classes + hideOnFloat + "\">")
			op("<div class=\"eptitleinside\">")
			opl(episode['name'] + "</div></th>")

		if isBody:
			printBodyCells(seasEpNum, totEpNum)

		opl("</tr>")

# This is currently unused, and probably doesn't work!
def printSeasonsUseRow():
	opl("<tr>")
	opl(_tab + "<td class=\"hidden\" colspan=\"2\"></td><td class=\"eptitle seasonsuse\">Seasons that use this chapter:</td>")
	for book in range(len(g_bookList)):
		n = 0
		op(_tab)
		for chap in range(g_bookNChap[book]):

			classes = "b" + str(book+1) + " bb"

			if (chap == g_bookNChap[book]-1):
				classes += " rb"
			elif (n == 0):
				classes += " lb"
			if n % _nStripe == 0:
				classes += " s"
			
			op("<td class=\""+classes+"\"></td>")
			n += 1
		op(_eol)
	opl("</tr>")

##### Main parsing function #####

def doParsing():
	global g_chapterList, g_bookList, g_interleavedChapterList
	global g_bookNChap, g_bookChapOffset
	global g_episodeList, g_connList

	g_chapterList, g_bookList, g_bookNChap = parseChapters()
	g_bookChapOffset = cumsum(g_bookNChap)

	#prepend 0 to start
	g_bookChapOffset[:0] = [0]

	print("")
	print(len(g_chapterList), "chapters in", len(g_bookList), "books:")
	for n in range(len(g_bookList)):
		print(n+1, g_bookList[n], '-', g_bookNChap[n], 'chapters, first chapter is', g_bookChapOffset[n]+1, 'overall')
	print("")

	combinedChapterList = parseCombinedOrder()

	print(len(combinedChapterList), "chapters in books 4+5")

	# Have to use list(), otherwise it just copies reference and that's bad
	g_interleavedChapterList = list(g_chapterList)
	# Insert combined chapter list into g_chapterList
	g_interleavedChapterList[g_bookChapOffset[5]:g_bookChapOffset[5]] = combinedChapterList

	if _debug:
		for chapter in g_interleavedChapterList:
			print(repr(chapter))

	print("")

	g_episodeList = parseEpisodes()
	numEpisodes = len(g_episodeList)
	print(repr(numEpisodes), "episodes")

	print("")

	g_connList = parseConnections()
	print(len(g_connList), "episode-chapter connections")

##### Main printing function #####

def doPrinting():
	global g_inFileInter, g_inFilePrint, g_outFileInter, g_outFilePrint, g_opInterVer, g_opPrintVer

	g_opInterVer = True
	g_opPrintVer = True

	print("Creating output file:", _outputFilenameInter)

	g_inFileInter = open(_htmlTemplateFilenameInter, 'r')
	g_inFilePrint = open(_htmlTemplateFilenamePrint, 'r')
	g_outFileInter = open(_outputFilenameInter,'w')
	g_outFilePrint = open(_outputFilenamePrint,'w')

	printHtmlHeader()

	opl("<div id=\"tablediv\" class=\"cpov spoiler_b0\">")

	##### Print floating table #####

	print("Writing floating table")

	g_opPrintVer = False

	opl("<table id=\"floatingtable\">")

	opl("<thead>")
	opl("<tr class=\"booktitlerow\">")
	opl(_tab + "<th colspan=\"3\" rowspan=\"2\" class=\"cornerbox rb\"><div class=\"cornerboxdiv\">" + _topLeftBox + "</div></th>")
	opl("</tr>")
	opl("<tr></tr>")
	opl("</thead>")

	printEpisodeRows(isBody=False)

	g_opPrintVer = False
	opl("</table>")

	##### thead #####

	print("Writing table chapter headers")

	g_opPrintVer = True

	opl("<div id=\"maintablediv\">")

	opl("<table id=\"maintable\">")
	opl("<thead>")
	opl("<tr class=\"booktitlerow\">")

	# Non-floating top-left box
	opl(_tab + "<th colspan=\"3\" rowspan=\"2\" class=\"cornerbox hideonfloat\"><div class=\"cornerboxdiv\">" + _topLeftBox + "</div></th>")

	printBookTitleCells()

	opl("</tr>")
	opl("<tr>")

	printChapterTitleCells()

	opl("</tr>")
	opl("</thead>")

	##### tbody #####

	opl("<tbody>")

	print("")
	print("***** Writing table body *****")
	print("")

	printEpisodeRows(isBody=True)

	opl("</tbody>")
	opl("</table>")
	opl("</div> <!-- /maintablediv -->")

	##### Print floating table - print version only #####

	g_opPrintVer = True
	g_opInterVer = False

	opl("<table id=\"floatingtable\">")

	opl("<thead>")
	opl("<tr class=\"booktitlerow\">")
	opl(_tab + "<th colspan=\"3\" rowspan=\"2\" class=\"cornerbox lb\"><div class=\"cornerboxdiv\">&nbsp;</div></th>")
	opl("</tr>")
	opl("<tr></tr>")
	opl("</thead>")

	printEpisodeRows(isBody=False, isEnd=True)

	opl("</table>")

	##### Done #####

	g_opPrintVer = True
	g_opInterVer = True
	opl("</div> <!-- /tablediv -->")

	print("")
	print("***** Table body complete *****")
	print("")

	printHtmlFooter()

	print("Closing HTML files")
	g_inFileInter.close()
	g_inFilePrint.close()
	g_outFileInter.close()
	g_outFilePrint.close()

##### process files #####

# Unused at the moment
def combineCss():
	print('Combining css')
	with open(_cssConcatFilename, 'w') as outfile:

		outfile.write('/*' + _eol)
		outfile.write('This is multiple css files concatenated together (so they can easily be gzipped)' + _eol)
		outfile.write('*/' + _eol)

		for basefname in _cssFilesToConcat:
			fname = join('output','css',basefname)
			with open(fname) as infile:
				outfile.write(_eol + '/* ' + basefname + ' */' + _eol + _eol)
				outfile.write(infile.read())

def gzipFile(filename):
	print('gzipping file', filename)
	with open(filename, 'rb') as f_in:
			with gzip.open(filename+'.gz', 'wb') as f_out:
					f_out.writelines(f_in)

def processOutputFiles():
	for fname in _filesToGzip:
		gzipFile(fname)

##### Processing starts here #####

if __name__ == "__main__":

	print("")
	print("Game of Thrones episode-chapter table generator")
	print(_copyrightInfo)
	print("")

	doParsing()

	print("")

	doPrinting()

	print("")

	processOutputFiles()

	print("")
	print("Complete!")
	print("")

