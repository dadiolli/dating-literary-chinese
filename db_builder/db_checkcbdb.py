"""
Use biographical and biblioghraphical information from CBDB 
to improve the HDC database
"""
from collections import namedtuple, Counter
from itertools import starmap
import logging, regex as re, sys, time
from mafan import simplify, tradify
from modules.initialize_logger3 import *
if __name__ == "__main__":
	initialize_logger("db_creation.log")
from progress.bar import ShadyBar
from modules.classes3 import HYDCDBook
from modules.dynasties3 import dynasty_handler
from modules.toolbox3 import database_connect

###########################################################
# Step 0, make some preparations
###########################################################

cbdb_bookdict, cbdb_dict = {}, {}
conn, cursor = database_connect()
cnt, ucnt, namecnt = Counter(), Counter(), Counter()

###########################################################
# Step 0.5, define custom functions and classes
###########################################################

class CBDBBook():
	def __init__(self, bid, title, py, en, year):
		self.id = bid
		# strip juan, as it is 寧波府志:三十六卷
		self.title = title.split(':')[0]
		# convert to jianti, as dhydcd will have 宁波府志
		self.jianti = simplify(self.title)
		self.py = py
		self.en = en
		self.year = year
		self.dynasty = dynasty_handler(self.year)[0]
		# self.distinct_author = None
		# self.author_id = None
		self.involved_people = []
		# get the list of involved people, if there are any
		cursor.execute("""SELECT `biog_main`.`c_personid`, `c_name_chn` 
			FROM `text_data` LEFT JOIN `biog_main` ON `text_data`.`c_personid` = `biog_main`.`c_personid` 
			WHERE `text_data`.`c_personid` > 0 
			AND `c_name_chn` IS NOT NULL AND `c_role_id` <= 3
			AND `text_data`.`c_textid` = %s""" % (self.id))
		results = cursor.fetchall()
		if len(results) >= 1:
			for r_id, r_name in results:
				# if len(results) == 1:
					# self.author_id = r_id
				person_jianti = simplify(r_name)
				self.involved_people.append((r_id, person_jianti))
		else:
			self.involved_people = None
	def distinct_name(self):
		if self.involved_people:
			if len(self.involved_people) == 1:
				return(self.involved_people[0][1], self.involved_people[0][0])
			else:
				return False
	def name_check(self, name_to_check):
		if self.involved_people:
			candidates = len(self.involved_people)
			for person_id, xingming in self.involved_people:
				if xingming in name_to_check:
					# add here if we want to count or gather repaired author names
					logging.debug("✅ " + xingming + " in " + name_to_check + ".")
					return(xingming, person_id, candidates)
			return False
		else:
			return False
	def chron_check(self, start, end):
		# give it a little tolerance
		return int(start) - 5 <= int(self.year) <= int(end) + 5

CBDBPerson = namedtuple('CBDBPerson', 'id, name, startyear, endyear')
HYDCDAuthor = namedtuple('HYDCDAuthor', 'startyear, endyear, name')

def overlap(a_start, a_end, b_start, b_end):
	logging.debug("HYDCD start: " + str(a_start) + " <= CBDB birth " + str(b_start) + " <= HYDCD end " + str(a_end) + " or CBDB start: " + str(b_start) + " <= HYDCD start " + str(a_start) + " <= CBDB end " + str(b_end))
	return a_start <= b_start <= a_end or b_start <= a_start <= b_end

###########################################################
# Step 1, check book titles
###########################################################

mismatched_authors = []
start_time = time.time()
# load book list from cbdb with relevant data we can get
logging.info('🤖 Fetching the data from CBDB...')
# prefer c_text_year, as it is mostly earlier; if it is null or 0, take c_pub_year
cursor.execute('''SELECT `c_textid`, `c_title_chn`, `c_title`, `c_title_trans`, 
	              		  ifnull(`c_text_year`, 0) the_year 
	              	FROM `text_codes` WHERE `c_title_chn` != '0'
	              	HAVING the_year != 0''')
cbdb_books = list(starmap(CBDBBook, cursor.fetchall()))
# prepare the cbdb books as a dictionary
for cb in cbdb_books:
	# honor duplicates here
	if cb.jianti in cbdb_bookdict:
		cbdb_bookdict[cb.jianti].append(cb)
	else:
		cbdb_bookdict[cb.jianti] = [cb]
	cbdb_dict[cb.id] = cb
logging.info('✅ Retrieved and stored information on %s books from CBDB.' % len(cbdb_books))

# load book list from the_books where data is needed
logging.info("🤖 Fetching the sources used in 漢語大詞典 from the database...")
cursor.execute('''SELECT `id`, `clearbook`, `author`, `startyear`, `endyear`, `dynasty`
					FROM `the_books` WHERE `source` is null or `source` = \'HYDCD\'
					AND `startyear` != `endyear`''')
hydcd_books = list(starmap(HYDCDBook, cursor.fetchall()))
bar = ShadyBar('⏳ Working.', max=len(hydcd_books), width=60)
logging.info('✅ Retrieving %s sources used in the 漢語大詞典 citations.' % len(hydcd_books))
for hb in hydcd_books:
	# check possible cbdb book matches
	match = False
	namecheck = False
	if hb.title in cbdb_bookdict:
		cb_list = cbdb_bookdict[hb.title]
		if hb.author:
			cbdb_book_id_candidates = [i.id for i in cb_list]
			# get person list for the book and check for matches
			for cb_id in cbdb_book_id_candidates:
				cb = cbdb_dict[cb_id]
				namecheck = cb.name_check(hb.author_jianti)
				if namecheck:
					cnt['author'] += 1
					update_type = "CBDB-title-author"
					match = cb
					break
				else:
					mismatched_authors.append((hb.author, hb.title))	
		# hydcd has chronological information
		if hb.startyear and match == False:
			logging.debug("ℹ️  Checking chron-match on %s (%s, %s)" % (hb.title, hb.startyear, hb.endyear))
			for cb in cb_list:
				if cb.chron_check(hb.startyear, hb.endyear):
					logging.debug("✅ %s (%s) matches timeframe %s–%s (%s)" % (cb.title, cb.year, hb.startyear, hb.endyear, hb.dynasty))
					cnt['chrono'] += 1
					update_type = "CBDB-title-chron"
					match = cb
					if not hb.author:
						namecheck = cb.distinct_name()
					break
				else:
					logging.debug("❎ %s (%s) does not fit timeframe %s–%s (%s vs. %s)" % (cb.title, cb.year, hb.startyear, hb.endyear, hb.dynasty, cb.dynasty))
			
		# hydcd has not much info, but the title is unique
		if len(cb_list) == 1 and match == False:
			match = cb_list[0]
			cnt['authorless'] += 1
			logging.debug('✅ Match' + str(hb.id) + hb.title + match.title + ' ' + str(match.year) + ' ' + str(match.id))
			update_type = "CBDB-title"
			if not hb.author:
				namecheck = cb.distinct_name()
	if match:
		if not namecheck:
			namecheck = (hb.author, None)
		cursor.execute("""UPDATE `the_books` 
			SET cbdb_text_id = %s, title_py = %s, title_western = %s, 
			    startyear = %s, endyear = %s, dynasty = %s, estimate = 0, 
			    source = %s, author = %s, cbdb_author_id = %s
			WHERE id = %s""", 
			(match.id, match.py, match.en, match.year, match.year, match.dynasty, update_type, namecheck[0], namecheck[1], hb.id))
		ucnt['direct'] += cursor.rowcount
		conn.commit()
	bar.next()
bar.finish()
logging.info("---")
logging.info('⏱  Checked %s primary sources from 漢語大詞典 against %s texts from CBDB in %.2f seconds.' % (len(list(hydcd_books)), len(cbdb_books), (time.time() - start_time)))
logging.info("🐍 Total matches: %s, total updates: %s." % (sum(cnt.values()), sum(ucnt.values())))
logging.info("🎏 Chronological matches: %s, ✏️  author and title matches: %s, 📕 title matches: %s." % (cnt['chrono'], cnt['author'], cnt['authorless']))
logging.debug("✏️  Unknown authors with known writings: " + ", ".join("%s《%s》" % tup for tup in mismatched_authors) + ".")
logging.info("---")

###########################################################
# Step 2, check author bio if it improves precision
###########################################################

start_time = time.time()
# load people from hydcd with startyear, endyear 
# group for perfomance
cursor.execute("""SELECT `startyear`, `endyear`, `author` from `the_books` 
				  WHERE (`source` is null or `source` = \'HYDCD\') and `author` is not null and `author` != ''
				  GROUP by `startyear`, `endyear`, `author`""")
hydcd_authors = map(HYDCDAuthor._make, cursor.fetchall())
logging.info('✅ We have ' + str(cursor.rowcount) + ' distinct ✏️  authors in the 漢語大詞典 citations.')

# get a list of people we have relevant data for, if they exist only once.
logging.info('🤖 Fetching biographical information from CBDB, this might take a while...')
cursor.execute("""SELECT `c_personid`, `c_name_chn`,
				    if(coalesce(`c_birthyear`,0) = 0, if(coalesce(`c_fl_earliest_year`,0) = 0, `c_index_year`, `c_fl_earliest_year`), `c_birthyear`) as startyear, 
				    if(coalesce(`c_deathyear`, 0) = 0, if(coalesce(`c_fl_latest_year`,0) = 0, `c_index_year`, `c_fl_latest_year`), `c_deathyear`) as endyear
				  FROM `biog_main` 
				  HAVING startyear != 0 and endyear != 0 and endyear >= startyear""")
cbdb_people_data = map(CBDBPerson._make, cursor.fetchall())
logging.info('✅ We have ' + str(cursor.rowcount) + ' people with biographical data in CBDB.')
c_list = set([simplify(person[1]) for person in cbdb_people_data])
h_list = set([simplify(author[2]) for author in hydcd_authors])
relevant_people = c_list & h_list
logging.info('🐍 Detected %s potential person matches.' % (len(relevant_people)))

cbdb_peopledict = {}
for person in cbdb_people_data:
	person_jianti = simplify(person.name)
	if person_jianti in cbdb_peopledict:
		cbdb_peopledict[person_jianti].append(person)
	else:
		cbdb_peopledict[person_jianti] = [person]
	namecnt[person_jianti] += 1
logging.info('🤖 Checking matches...')
bar = ShadyBar('⏳ Working.', max=len(list(hydcd_authors)), width=60)

for author in hydcd_authors:
	# TODO: change order how this is done!
	author_jianti = simplify(author.name)
	if author_jianti in relevant_people:
		lookup = cbdb_peopledict[author_jianti]
		# check if one of the timespans is okay
		if author.startyear:
			for person in lookup:
				chroncheck = overlap(author.startyear, author.endyear, person.startyear, person.endyear)
				if chroncheck == True:
					cnt['author-chrono'] += 1
					# might still want to check all to gather some interesting data!
					cursor.execute("""UPDATE `the_books` 
						SET `startyear` = %s, `endyear` = %s, estimate = 1, source = 'CBDB-author' 
						WHERE `author` = %s and `startyear` = %s and `endyear` = %s 
						AND `endyear` - `startyear` >= %s""", (person.startyear, person.endyear, author.name, author.startyear, author.endyear, person.endyear - person.startyear))				
					ucnt['author-chrono'] += cursor.rowcount
					break
			if chroncheck == False:
				cnt['author-no-chrono'] += 1
		# if there's no time to check against, check distinct name
		else:
			logging.debug('HYDCD author ' + author_jianti + '(' + author.name + ') has no chron info, has ' + str(len(lookup)) + ' name matches.')
			if len(lookup) == 1:
				cnt['author-distinct'] += 1
				cursor.execute("""UPDATE `the_books` 
					SET `startyear` = %s, `endyear` = %s, estimate = 1, source = 'CBDB-author' 
					WHERE `author` = %s and `startyear` is null and `endyear` is null""", (lookup[0].startyear, lookup[0].endyear, author.name))
				ucnt['author-distinct'] += cursor.rowcount				
		conn.commit()
	bar.next()
bar.finish()	
logging.info("---")
logging.info('⏱  Checked %s authors from 漢語大詞典 against %s persons from CBDB in %.2f seconds.' % (len(list(hydcd_authors)), len(cbdb_peopledict), (time.time() - start_time)))
logging.info("🎏 Chronological matches: %s, updated %s HYDCD sources" % ((cnt['author-chrono']), ucnt['author-chrono']))
logging.info("🎏 Chronological mismatches: " + str(cnt['author-no-chrono']))
logging.info("✏️  No chronological info, but distinct author name matches: %s, updated %s HYDCD sources." % (cnt['author-distinct'], cnt['author-distinct']))
logging.info("---")
logging.info("🐍 Improved HYDCD source information on a total of %s entries." % (sum(ucnt.values())))

###########################################################
# Fine
###########################################################

cursor.close()
conn.close()