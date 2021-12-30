import regex as re, sys, time

# make some preparations
from collections import Counter
from progress.bar import ShadyBar
from modules.toolbox3 import create_truncate_table, database_connect, unbreak
from modules.dynasties3 import dynastylist, startswithdynastyregex
from modules.cidianregexp import pinyinpattern, pronunciationpattern, rhymepattern, starentrypattern, subentrypattern, zhuyinpattern
from modules.initialize_logger3 import *
from modules.tables import hydcd_entries, hydcd_words

if __name__ == "__main__":
	initialize_logger('db_creation.log')

########################################################
# Define a function to handle word and char entries
########################################################

def subentry_handler(subentry, content):
	"removes all the patterny characters from the word-entry words"
	if '【' in subentry:
		cleanword = ''.join(c for c in subentry if c not in '【】012345789 ' )
		entrytype = 'W'
		word = subentry
		pinyin, bopomofo, rhyme = None, None, None
	elif '［' in subentry:
		pronunciation = re.search(pronunciationpattern, subentry).group(1)
		try:
			bopomofo = re.search(zhuyinpattern, pronunciation).group(1)
		except:
			logging.debug(pronunciation + ": missing Zhuyin." )
			bopomofo = None
		try:
			pinyin = re.search(pinyinpattern, pronunciation).group(1)
		except:
			logging.debug(subentry + ": missing Pinyin.")
			pinyin = None
		try: # move rhyme info 
			rhyme = re.search(rhymepattern, content).group(1)
		except:
			rhyme = None
		content = re.sub(pronunciationpattern, '', content)
		content = re.sub(rhymepattern, '', content)
		cleanword = re.sub(u'[^\p{IsHan}]', '', subentry)
		entrytype = 'C'
		word = '【' + cleanword + '】'
	else:
		return(None)
	return(word, cleanword, entrytype, pinyin, bopomofo, rhyme, content)


########################################################
# Read the hydcd plain text file to the database
########################################################
try:
	hanyudacidian = open('../hydcd/hanyudacidian.txt').read()
except:
	hanyudacidian = open('hydcd/hanyudacidian.txt').read()
all_starentries = re.split(starentrypattern, hanyudacidian) 

logging.info("✅  The dictionary has been loaded.")


conn, cursor = database_connect()
create_truncate_table(cursor, conn, hydcd_entries, 'hydcd_entries')
create_truncate_table(cursor, conn, hydcd_words, 'hydcd_words')

logging.info('🐍  Entries are being structured into the database.')
starttime = time.time()
bar = ShadyBar('⏳  Working.', max=len(all_starentries)/2, width=60)
cnt = Counter({'total': 1, 'star': 1})

########################################################
# Outer loop: main character entries
########################################################
for j in range(1, len(all_starentries), 2): #step 2, because every second finding is the pattern match
	char, entry = all_starentries[j], all_starentries[j].replace('*','') + all_starentries[j+1]
	cursor.execute('insert into `hydcd_entries` (id, `char`, `entry`) values (%s, %s, %s)', (cnt['star'], char, entry))
	subentries = re.split(subentrypattern, entry)
	cnt['internal'] = 1 	
	########################################################
	# Inner loop: word and heteronym entries
	########################################################
	for l in range(1, len(subentries), 2):
		subentry = unbreak(subentries[l+1])
		word, cleanword, entrytype, pinyin, zhuyin, rhyme, content = subentry_handler(subentries[l], subentry)
		cursor.execute("""insert into `hydcd_words` (
				id, id_internal, char_id, `char`, `word`, `cleanword`, `zhuyin`, 
				`pinyin`, `rhyme`, `entry`, `entrytype`) 
				values 
				(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""", 
			(cnt['total'], cnt['internal'], cnt['star'], char, word, cleanword, zhuyin, pinyin, rhyme, content, entrytype))
		cnt['internal'] += 1
		cnt['total'] += 1
		if entrytype == 'C': cnt['char'] += 1
		if entrytype == 'W': cnt['word'] += 1
	cnt['star'] += 1 # new main character entry
	conn.commit()
	bar.next()
bar.finish()
logging.info('⏱ %s entries in %.2f seconds (%.0f entries per second). ' % (cnt['total']-1, (time.time() - starttime), (cnt['total']-1)/(time.time() - starttime)))
logging.info('🐍 %s word entries, %s star entries, %s character entries. ' % (cnt['word'], cnt['star']-1, cnt['char']))
cursor.close()
conn.close()