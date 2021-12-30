################################################################
# Generate word pronunciation
################################################################

import logging, regex as re, sys, time
from progress.bar import ShadyBar
from modules.toolbox3 import database_connect
from modules.initialize_logger3 import *
if __name__ == "__main__":
	initialize_logger("db_creation.log")

conn, cursor = database_connect()

logging.info('🐍 Generating 拼音 / 注音 pronunciation for words.')
starttime = time.time()

################################################################
# Get word entries we want to generate pronunciation for
################################################################

cursor.execute("select id, word from hydcd_words where entrytype = 'W' order by id asc;")
wordentrylist = list(cursor.fetchall())	
logging.info('✅  Retrieved %s entries from the dictionary.' % len(wordentrylist))

################################################################
# Retrieve the pronunciation info for the character
################################################################

cursor.execute("select id_internal, cleanword, zhuyin, pinyin from hydcd_words where entrytype = 'C' order by id asc;")
pronunciationlist = list(cursor.fetchall())
pronunciationdictionary = {}
[pronunciationdictionary.update({(i, c):(bopo, py)}) for i, c, bopo, py in pronunciationlist]
logging.info('✅  Gathered pronunciation information from %s character entries from the dictionary.' % len(pronunciationlist))
charpattern = re.compile('(\p{IsHan}[0-9]?)', re.UNICODE)
bar = ShadyBar('⏳  Working.', max=len(wordentrylist), width=60)

################################################################
# Build the word pronunciation string and write to the database
################################################################

for wordentry in wordentrylist: #【下2一鉤子】
	word_id, word = wordentry[0], wordentry[1].replace(' ', '').replace('【', '').replace('】','') 	
	charlist = re.findall(charpattern, word)
	wordzhuyin, wordpinyin = '', ''
	for char in charlist:
		if len(char) == 1: 
			id_internal = 1
		else: # this is duoyinzi with diff. pronunciations.
			id_internal = int(char[1])
			char = char[0]
		try: 
			zhuyin, pinyin = pronunciationdictionary[(id_internal, char)]
		except:
			zhuyin, pinyin = '___', '___'		
		wordzhuyin += zhuyin
		wordpinyin += pinyin
	cursor.execute("update hydcd_words set zhuyin = %s, pinyin = %s where id = %s", (wordzhuyin, wordpinyin, word_id))
	conn.commit()
	bar.next()
bar.finish()
cursor.close()
conn.close()
logging.info('⏱  Finished this in no time. %s entries updated in %.2f seconds (%.0f entries per second). ' % (len(wordentrylist), (time.time() - starttime), len(wordentrylist)/(time.time() - starttime)))