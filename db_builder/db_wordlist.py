# -*- coding: utf-8 -*-
import logging, sys, time
from modules.toolbox3 import database_connect
from modules.initialize_logger3 import *
from progress.bar import ShadyBar

if __name__ == "__main__":
	initialize_logger("db_creation.log")

conn, cursor = database_connect()
logging.info('🐍 Creating 2 flavors of lexeme list from `the_words`')
cursor.execute("SELECT w.cleanword, w.nakedword from the_words w order by `id` asc")
hydcd_entries = cursor.fetchall()
logging.info('✅ Retrieved %s word entries from the database at %s.' % (cursor.rowcount, time.ctime()))

bar = ShadyBar('⏳ Working.', max=2*cursor.rowcount, width=60)
with open('../hydcd/wordlist_punctuation_true.txt', 'w') as f:
	for word in hydcd_entries:		
		f.write("%s\n" % word[0])
		bar.next()

with open('../hydcd/wordlist_punctuation_false.txt', 'w') as f:
	for word in hydcd_entries:
		f.write("%s\n" % word[1])
		bar.next()
bar.finish()

logging.info('🐍 Also loading full HYDCD lexeme list from `hydcd_words`')
cursor.execute("SELECT w.cleanword from hydcd_words w order by `id` asc")
hydcd_entries = cursor.fetchall()
logging.info('✅ Retrieved %s word entries from the database at %s.' % (cursor.rowcount, time.ctime()))

bar = ShadyBar('⏳ Working.', max=cursor.rowcount, width=60)
with open('../hydcd/wordlist_full_punctuation_true.txt', 'w') as f:
	for word in hydcd_entries:		
		f.write("%s\n" % word[0])
		bar.next()
bar.finish()

logging.info('✅ Created / updated the lexeme lists with and without punctuation at %s.' % (time.ctime()))