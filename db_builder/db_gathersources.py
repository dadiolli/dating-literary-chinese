# -*- coding: utf-8 -*-
import logging, regex as re, sys, time
from modules.initialize_logger3 import *
from collections import Counter
from progress.bar import ShadyBar
from modules.cidianregexp import *
from modules.cleanhan3 import hanonly
from modules.dynasties3 import dynastydict, startswithdynastyregex, dynasty_handler
from modules.tables import the_books, the_words
from modules.toolbox3 import create_truncate_table, database_connect, unbreak
import pandas as pd

################################################################
# Select run mode
################################################################

mode = 'run'
debugentry = ['謟過','謡讟','石油','崑山','一刀兩段','一二九運動','一列','七覺分']
# 一二九運動 no citation
# 一刀兩段 citation not in first subentry
# 崑山 X 詩, X 注引 Y patterns as source
# 謡讟 difficult author 唐陆贽
# 謟過 X 注 Y
# 一列 will ensure double use of a source
# 七覺分, has interesting bracketing

loglevel = logging.DEBUG if mode == 'debug' else logging.INFO

################################################################
# Define a useful data type
################################################################

class CitedBook():
	def __init__(self, raw):
		self.raw = raw
		self.fullbook = re.sub("[《》]", "", raw) # without pattern chars
		self.book = self.fullbook.replace('，','·').split('·')[0] # only the main book title
		self.dynasty, self.author, self.year = None, None, None
		self.startyear, self.endyear = None, None
		self.source, self.estimate = None, None

	def identify(self):
		"returns a hash of the identifier tuple"
		identifier = hash((self.book, self.dynasty, self.author, self.year))
		return(identifier)

################################################################
# Define functions
################################################################
def get_subentries(entry):
	"Splits an entry into it's subentries"
	entrylist = []
	if '1.' in entry[0:21]: # then it has subentries
		fragments = re.split(splitentrypattern, entry) # if yes, split it		
		for i in range(3,len(fragments),3):
			entrylist.append(fragments[i])
		return(entrylist)
	else: 
		entrylist = [entry]
		return(entrylist)

def get_sourceinfo(headword, fragment):
	"Extracts all source metadata from a HYDCD subentry"
	all_sourcefindings = re.findall(citepatternyear, fragment)
	sources = {}
	if len(all_sourcefindings) == 0:
		return(None)
	for i, finding in enumerate(all_sourcefindings):
		source = CitedBook(raw = finding)
		regex = re.compile('[^)(*.“’””’。，；？！：、》>…】（）［］]{2,9}(?=' + source.raw + ')', re.UNICODE)
		da = re.search(regex, fragment)
		dynastyauthor = da.group() if da else None
		########################################################
		# Year
		########################################################
		y = re.search("\d{4}", str(dynastyauthor) + source.raw)
		year = y.group(0) if y else None
		logging.debug('Year was detected as %s, will skip dynasty or author if not None.' % (year))
		if year:
			year = int(year) # catch "chinese" numbers as well
			source.year, source.startyear, source.endyear = year, year, year
			source.dynasty = dynasty_handler(year)[0]
			source.source, source.estimate = 'HYDCD', 0
			sources[i] = source
			continue

		############################################################
		# Author and Dynasty
		############################################################	
		if dynastyauthor:
			logging.debug('Dynasty / author candidate was detected as %s.' % dynastyauthor)
			# remove stuff that can't be an author name
			dynastyauthor_cleaned = re.sub(authornametaboos, '', dynastyauthor)
			logging.debug('String cleaned to %s.' % dynastyauthor_cleaned)
			# check if only a dynasty name is given and exit if so
			if dynastyauthor_cleaned in dynastydict:
				source.dynasty = dynastyauthor_cleaned
				source.startyear, source.endyear = dynastydict[source.dynasty]
				source.source, source.estimate = 'HYDCD', 2
				sources[i] = source
				continue
			# longer than 2 chars: can hold dynasty + author
			if len(dynastyauthor_cleaned) > 2:
				# ??? auch weiter hinten nach der Dynastie schauen?
				# z. B. für 稗海本 晋 干宝
				# wenn nach dem Treffer noch 2+ Zeichen für den Namen bleiben
				dyn = re.search(startswithdynastyregex, dynastyauthor_cleaned)
				if dyn:
					source.dynasty = dyn.group()
					source.author = dynastyauthor_cleaned[len(source.dynasty):] # string after dynasty
			if not source.dynasty and len(dynastyauthor_cleaned) >= 2:
				source.author = dynastyauthor_cleaned # might be only the author
			if len(dynastyauthor_cleaned) <= 2: # less than 2 chars: not good enough
				source.author = dynastyauthor_cleaned
			if source.author and source.dynasty: # both there? great, but we want to make sure
				if ((len(source.author) <= 3) and (len(dynastyauthor_cleaned) <= 3) and (source.author[0] not in nondynasty_surnamestarters) and (source.author[0] not in dynastysurnames)): 
					source.author = dynastyauthor_cleaned
					source.dynasty = None
					repaired_authors[source.author] += 1
					logging.debug('%s: %s surname in %s was originally mistaken for dynasty, fixed.' % (headword, source.author[0], source.author))			
			if source.author in sourcemappings:
				source.dynasty, source.author = sourcemappings[source.author][0], sourcemappings[source.author][1]
			if source.dynasty:
				source.startyear, source.endyear = dynastydict[source.dynasty]
				source.source = 'HYDCD'
				source.estimate = 1 if source.author else 2
			if source.author and len(source.author) > 7: # max. is 爱新觉罗·溥仪
				prevented_authors[source.author] += 1
				source.author = None
				logging.debug("%s: Prevented author: %s" % (headword, source.author))
			if source.author and len(source.author) <= 1:
				source.author = None
		sources[i] = source
	return(sources)

################################################################
# Initialize variables
################################################################

if __name__ == "__main__":
	initialize_logger("db_creation.log")
cnt, usecount, useinfirstcount = Counter(), Counter(), Counter()
sourcedict, sourcedata, unordered_entries = {}, {}, []
repaired_authors, prevented_authors = Counter(), Counter()
citationdata = []

logging.info("")

################################################################
# Create the_words table
################################################################
conn, cursor = database_connect()

if mode != 'debug':
	from modules.tables import the_words
	create_truncate_table(cursor, conn, the_words, 'the_words')

################################################################
# Gather dictionary data
################################################################

logging.info('🤖  Fetching the word entries from the database. This might take a while...')
#                 0     1       2        3         4
select = 'SELECT `id`, `word`, `entry`, `pinyin`, `cleanword` FROM `hydcd_words` '
if mode == 'debug':
	select += "WHERE `cleanword` in ('%s') " % ( "', '".join(debugentry) )
select += 'ORDER by `id`' 
cursor.execute(select)
hydcd_entries, entrycount = cursor.fetchall(), cursor.rowcount
logging.info('✅  Retrieved %s word entries from the database at %s.' % (entrycount, time.ctime()))
start_time = time.time()

bar = ShadyBar('⏳  Working.', max=entrycount, width=60)

################################################################
# Process all the entries into a words table linked to sources
################################################################

for entry_id, word, content, pinyin, cleanword in hydcd_entries:
	############################################################
	# Initialize
	############################################################
	logging.debug('\n➡️  ' +  word + ' is analyzed.' )
	first_subentry_has_source, entry_has_source,first_source = 0, False, False
	check_entry_order, word_inserted, findings = False, False, []
	entrylist = get_subentries(content)		
	cnt['subentries'] += len(entrylist)

	############################################################
	# Process sub-subentries
	############################################################
	
	for fragment_id, fragment in enumerate(entrylist):
		logging.debug('Entry or fragment %s: %s' % (fragment_id, fragment))
		sources = get_sourceinfo(word, fragment)
		if sources:
			entry_has_source = True
			cnt['sourcefound'] += 1
			# only writes to DB first source, checking also if first subentry has the source
			for j, source in sources.items():
				first_subentry_source = False
				logging.debug('Found source %s: %s (%s), dynasty: %s, author: %s, year: %s–%s.', j, source.fullbook, source.book, source.dynasty, source.author, source.startyear, source.endyear)
				if j == 0 and fragment_id == 0:
					first_subentry_has_source = 1
					first_subentry_source, first_source = True, True
					cnt['sourceinfirst'] += 1
				# catch the first source 
				if j == 0 and fragment_id > 0 and first_subentry_has_source == 0 and first_source == False:
					first_source = True
					cnt['indirectsource'] += 1
				# manage source ID
				identifier = source.identify()
				if identifier in sourcedict:
					book_id = sourcedict[identifier]
					useinfirstcount[book_id] += first_subentry_source
					usecount[book_id] += 1
				else:
					cnt['book_id'] += 1                     # give it a new id
					book_id = cnt['book_id']
					if source.year: cnt['year'] += 1        # generate some statistics 
					if source.dynasty: cnt['dynasty'] += 1
					if source.author: cnt['author'] += 1
					useinfirstcount[book_id] += first_subentry_source
					usecount[book_id] += 1
					sourcedict[identifier] = book_id
					sourcedata[book_id] = source						
				# write to DB
				if first_source and not word_inserted:					
					nakedword = hanonly(cleanword)
					if mode != 'debug':
						cursor.execute('insert into `the_words` (id, cleanword, nakedword, pinyin, firstentry, indirectsource, book, book_id) values (%s, %s, %s, %s, %s, %s, %s, %s)', 
							(entry_id, cleanword, nakedword, pinyin, source.fullbook, first_subentry_has_source, source.book, book_id))
						conn.commit()
					word_inserted = True
					cnt['entry_has_source'] += 1
					if source.dynasty and len(entrylist) > 0: # if first entry has dynasty (many won't, 詩經, 書 etc.), check the entry order
						cnt['order_check'] += 1 
						check_entry_order = True # might want to check this entry later									
				if check_entry_order and source.dynasty and j == 0: # gather first source of each subentry
					findings.append((source.fullbook, source.book, cnt['book_id'], source.dynasty, source.startyear, source.endyear)) # add to the list of findings
				citationdata.append((entry_id, fragment_id, book_id))
	if first_subentry_has_source == 0 and entry_has_source:
		cnt['sourcenotinfirst'] += 1
		# add some method to write word entry to db
	
	############################################################
	# Check entry order, if necessary
	############################################################

	if len(findings) > 1 and check_entry_order: # entry is fine if it has length 1		
		sorted_findings = sorted(findings, key=lambda x: x[4])
		if sorted_findings[0] != findings[0]: # not fine chronologically
			unordered_entries.append(word)
			if mode != 'debug':
				cursor.execute('update `the_words` set firstentry = %s, book = %s, book_id = %s, unordered = %s where id = %s', 
					(sorted_findings[0][0], sorted_findings[0][1], sorted_findings[0][2], 1, entry_id))
				conn.commit()
			logging.debug('Detected and fixed an unordered word entry %s' % word)	
	bar.next()
bar.finish() 

################################################################
# Print some statistics
################################################################

logging.info('---')
logging.info('ℹ️  There were %s findings where first sub-entry had no citation, %s of which have later citation.' % (cnt['sourcenotinfirst'], cnt['indirectsource']))
logging.info('📕  Found source in first subentry in %s of %s dictionary entries (%.2f percent).' % (cnt['sourceinfirst'], entrycount, (cnt['sourceinfirst'] / float(entrycount)) * 100))
logging.info('📕  %s of %s entries (%.2f percent), %s of %s subentries (%.2f percent) had sources.' % (cnt['entry_has_source'], entrycount, (cnt['entry_has_source'] / float(entrycount) * 100), cnt['sourcefound'], cnt['subentries'], (cnt['sourcefound'] / float(cnt['subentries'])) * 100))
logging.info('📕  %s citations in total, featuring %s unique sources (not differentiating between 卷 or chapter).' % (len(citationdata), len(sourcedata)))
logging.info('⏱  Analyzed %s source references in %s subentries in %.2f seconds.' % (len(citationdata), cnt['subentries'], (time.time() - start_time)))
logging.info('✏️  ' + str(sum(repaired_authors.values())) + ' possible dynasty / author matches were detected as »author only«: ')
logging.info(", ".join("%s (%sx)" % tpl for tpl in repaired_authors.most_common(100)) + '.')
logging.info('🐍  ' + str(sum(prevented_authors.values())) + ' possible dynasty / author matches were detected as »not the author«: ')
logging.info(", ".join("%s (%sx)" % tpl for tpl in prevented_authors.most_common(100)) + '.')
logging.info('---')
logging.info('🔀  %s were marked unordered because of their unchronological mention of dynasties.' % (len(unordered_entries)))
logging.info(', '.join(unordered_entries))
if mode != 'debug':
	logging.info('🐍  That is %.2f percent of %s tested entries with multiple dynasties and dynasty in first subentry.' % ((len(unordered_entries) / float(cnt['order_check']) * 100), cnt['order_check']))

################################################################
# Write the source list to the database
################################################################

if mode != 'debug':
	logging.info('---') 
	logging.info('🤖  Now building up `the_books` table...')
	from modules.tables import the_books
	create_truncate_table(cursor, conn, the_books, 'the_books')

	bar = ShadyBar('⏳  Working.', max=len(sourcedata), width=60)
	for book_id, source in sourcedata.items():
		cursor.execute('insert into `the_books` (id, clearbook, startyear, endyear, dynasty, estimate, usecount, useinfirstcount, source, author) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)', 
			(book_id, source.book, source.startyear, source.endyear, source.dynasty, source.estimate, usecount[book_id], useinfirstcount[book_id], source.source, source.author))
		conn.commit()
		bar.next()
	bar.finish()

	################################################################
	# Print some more statistics on sources
	################################################################

	logging.info('---')
	logging.info("✅  The list of %s sources has been stored." % (len(sourcedata)))
	logging.info('🎏  Found year in %s of %s sources (%.2f percent).' % (cnt['year'], len(sourcedata), (cnt['year'] / float(len(sourcedata))) * 100))
	logging.info('☀️  Found dynasty in %s of %s sources (%.2f percent).' % (cnt['dynasty'], len(sourcedata), (cnt['dynasty'] / float(len(sourcedata))) * 100))
	logging.info('✏️  Found author for %s of %s sources (%.2f percent).' % (cnt['author'], len(sourcedata), (cnt['author'] / float(len(sourcedata))) * 100))

	################################################################
	# Write the entry / source reference list to the database
	################################################################

	logging.info('---') 
	logging.info('🤖  Now building up `the_citations` table...')
	from modules.tables import the_citations
	create_truncate_table(cursor, conn, the_citations, 'the_citations')

	bar = ShadyBar('⏳  Working.', max=len(citationdata), width=60)
	for word_id, sub_id, book_id in citationdata:
		cursor.execute('insert into `the_citations` (word_id, sub_id, book_id) values (%s, %s, %s)', 
			(word_id, sub_id, book_id))
		conn.commit()
		bar.next()
	bar.finish()
	cursor.close()
	conn.close()

	################################################################
	# Print some more final statistics on sources
	################################################################

	logging.info('---')
	logging.info("✅  The list of %s source usages has been stored." % (len(citationdata)))
	logging.info('🐍  There\'s an average of %.2f citations per entry, average source usage is %.2f times.' % (len(citationdata) / len(hydcd_entries), len(citationdata) / len(sourcedata)))