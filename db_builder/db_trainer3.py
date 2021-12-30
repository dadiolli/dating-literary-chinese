# -*- coding: utf-8 -*-
"""
Iterate over a corpus of dated texts in order to train the database w/ earlier attestations
"""
###########################################################
# load python and own modules and get prepared
###########################################################

import pandas as pd, sys, time
from collections import Counter
from itertools import starmap
from modules.classes3 import ResearchText, HYDCDBook, HYDCDWord, TextFrequencies
from modules.initialize_logger3 import *
from modules.settings3 import settings_trainer as settings
from modules.toolbox3 import database_connect, select_builder
from progress.bar import ShadyBar

if __name__ == "__main__":
	initialize_logger("trainer.log")

start_time = time.time()

corpus_files = pd.read_csv('primary_sources/trainer_filemapping.csv', index_col='filename')
# corpus_files = pd.read_csv('primary_sources/trainer_filemapping_test.csv', index_col='filename')
corpus_files = corpus_files.fillna(0) 
dict_entries = set(open('hydcd/wordlist_punctuation_true.txt', 'r').read().split('\n'))
counter = Counter()

conn, cursor = database_connect()
for corpus_text in corpus_files.index.tolist():
	if corpus_files.hydcd_name[corpus_text]:
		texthydcdname = corpus_files.hydcd_name[corpus_text]
		file = open("primary_sources/" + corpus_files.corpus[corpus_text] + '/' + str(corpus_text))
		logging.info("🐼 " + corpus_text + " (" + texthydcdname + ") is analyzed.")
		text = ResearchText(file, punctuation=True, tradify=True, standardize=True)
		# use earlierst, grab id for largest useinfirstcount if several
		statement = ("select id, clearbook, author, startyear, endyear, dynasty from `the_books` where clearbook = '%s' and startyear is not null order by startyear asc, useinfirstcount desc limit 1" % corpus_files.hydcd_name[corpus_text])
		cursor.execute(statement)
		hydcd_book = HYDCDBook(*cursor.fetchall()[0])

		###########################################################
		# perform statistical tasks on the text
		###########################################################

		frequencies = TextFrequencies(text, settings)
		logging.info("Checking %s n-grams appearing %s or more times in the input text against %s entries in the dictionary." % (frequencies.freqlistlength, settings['LookupMinimumNgramCount'], len(dict_entries)))
		words = (frequencies.freq_grams & dict_entries) # intersect
		logging.info("Of these %s, %s were found to be 漢語大詞典 words." % (frequencies.freqlistlength, len(words)))
		
		###########################################################
		# select current hydcd datings for words
		###########################################################

		sql = select_builder(words, settings)
		logging.info('Loading dictionary entries...')
		cursor.execute(sql)
		word_sources = list(starmap(HYDCDWord, cursor.fetchall()))
		logging.info(str(cursor.rowcount) + ' corresponding dictionary entries with citation and year were retrieved from the database.')

		###########################################################
		# iterate through words
		###########################################################

		bar = ShadyBar('Working.', max=len(word_sources), width=60)
		for i, word in enumerate(word_sources):
			# print("%s: %s that has this word is dated to %s, word is currently dated to %s." % (word.cleanword, hydcd_book.title, hydcd_book.startyear, word.startyear))
			if (int(hydcd_book.startyear) < int(word.startyear) or (int(hydcd_book.endyear) < int(word.endyear))):
				if hydcd_book.endyear < word.endyear:
					logging.debug("Updating %s with evidence from %s (%s, %s)." % (word.cleanword, hydcd_book.title, hydcd_book.startyear, hydcd_book.endyear))
					update = ("update the_words set earliest_evidence_book_id = %s where id = %s" % (hydcd_book.id, word.id))
					cursor.execute(update)
					conn.commit()
					counter[hydcd_book.title] += 1
			bar.next()
		bar.finish()

	else:
		logging.info("📕 Insufficient information on " + corpus_text + ".")

for k, v in counter.most_common():
	print(k, v)
cursor.close()
conn.close()