# -*- coding: utf-8 -*-

###########################################################
# load python and own modules and get prepared
###########################################################

import pandas as pd, sys, time
from collections import Counter
from itertools import starmap
from modules.classes3 import CAFrequencies, CAGrams
from modules.initialize_logger3 import *

from modules.toolbox3 import database_connect, select_builder
from progress.bar import ShadyBar

if __name__ == "__main__":
	initialize_logger("trainer.log")
start_time = time.time()

settings = {'MinGram': 1, 
			'MaxGram': 3, # this is max. we get from CrossAsia
			'Sample': 1000,
			'Punctuation': True,
            'UseNonHYDCDEvidence': True,
            'UseDFZTraining': True,
            'HYDCDStandardize': True
			}

# get texts we need to exclude from the trainer, as they are our testing sample
# exclude_meta = pd.read_csv('results/chronon_observations_difangzhi-gramswords_1to2_20191218-150319.csv', index_col='filename') # get meta data
exclude_meta = pd.read_csv('../hydcd2017/results/chronon_observations_difangzhi-gramswords_1to2_20201205-114042.csv', index_col='filename') # get meta data


# get a sample of 5.000 other texts with useful chronological data
corpus = CAGrams('difangzhi-grams', 'difangzhi-metadata.xlsx', settings['Sample'], minchronon = -700, exclude=exclude_meta.index)
logging.info("🐼 Metadata for %s texts from 地方誌 is available." % (len(corpus.metadata)))
logging.info("🐼 Using metadata for %s texts." % (len(corpus.sample)))
dict_entries = set(open('hydcd/wordlist_punctuation_true.txt', 'r').read().split('\n'))
counter = Counter()

conn, cursor = database_connect()

try:
	cursor.execute("ALTER TABLE biog_main ADD COLUMN earliest_evidence_dfz_id varchar(32) DEFAULT null")
	cursor.execute("ALTER TABLE addresses ADD COLUMN earliest_evidence_dfz_id varchar(32) DEFAULT null")
except Exception as ex:   
	print(ex)

# Destroy results from test runs!
cursor.execute("DELETE from the_books where source = 'DFZ'")
cursor.execute("UPDATE the_words set earliest_evidence_dfz_id = NULL where earliest_evidence_dfz_id is not NULL")
cursor.execute("UPDATE biog_main set earliest_evidence_dfz_id = NULL, earliest_evidence_firstyear = NULL where earliest_evidence_dfz_id is not NULL")
cursor.execute("UPDATE addresses set earliest_evidence_dfz_id = NULL, earliest_evidence_firstyear = NULL where earliest_evidence_dfz_id is not NULL")
conn.commit()
cursor.execute("SELECT max(id)+1 from the_books")
start_id = cursor.fetchall()[0][0]

for i, sourcefile in enumerate(corpus.sample.index):
	id_external = start_id + i
	logging.info("🐍 Running trainer on %s (file: %s), pass %s of %s." % (corpus.sample.dc_title[sourcefile], sourcefile, i+1, len(corpus.sample.index)))
	
	sql = """INSERT into the_books (id, clearbook, startyear, endyear, dynasty, source, dfz_id) VALUES
		  (%s, '%s', %s, %s, '%s', 'DFZ', '%s')""" % (id_external, corpus.sample.dc_title[sourcefile], corpus.sample.startyear[sourcefile], corpus.sample.endyear[sourcefile], corpus.sample.dynasty[sourcefile], sourcefile)
	try:
		cursor.execute(sql)
	except Exception as ex:
		print(ex)
		print(sql)
		exit()
	else:
		conn.commit()
	
	###########################################################
	# get words:
	###########################################################
	
	# if difangzhi.endyear < hydcd.startyear or 
	# difangzhi.endyear < hydcd.endyear and difangzhi.interval < hydcd.interval
	# additionally coalesce on earliest_evidence_dfz_id to be up-to-date
	# where (endyear is null or startyear > %s or (endyear > %s and (endyear - startyear) > %s))
	sql = """SELECT cleanword from the_words w 
			 left join the_books b on coalesce(w.earliest_evidence_dfz_id,coalesce(w.earliest_evidence_book_id, w.book_id)) = b.id
			 where (%s < startyear or (%s < startyear and (endyear - startyear) > %s))
			 and length(cleanword) <= %s * 3""" % (corpus.sample.endyear[sourcefile], corpus.sample.startyear[sourcefile], corpus.sample.interval[sourcefile], settings['MaxGram'])
	cursor.execute(sql)
	dict_entries = set([item[0] for item in cursor.fetchall()])

	###########################################################
	# get names:
	###########################################################

	# if difangzhi.endyear < cbdb.startyear:
	sql = """SELECT c_name_chn, 
		coalesce(earliest_evidence_firstyear, if(coalesce(`c_birthyear`,0) = 0, if(coalesce(`c_fl_earliest_year`,0) = 0, `c_index_year`, `c_fl_earliest_year`), `c_birthyear`)) as startyear,
		if(coalesce(`c_birthyear`,0) = 0, if(coalesce(`c_fl_earliest_year`,0) = 0, `c_index_year`, `c_fl_earliest_year`), `c_birthyear`) as endyear 
			from biog_main where length(c_name_chn) >= 6 and length(c_name_chn) <= %s * 3
			and occurs = 1 	
			HAVING startyear != 0 and endyear != 0 and endyear >= startyear and %s < startyear
		  """ % (settings['MaxGram'], corpus.sample.endyear[sourcefile])
	cursor.execute(sql)
	cbdb_names = set([item[0] for item in cursor.fetchall()])

	###########################################################
	# get places:
	###########################################################

	# if difangzhi.endyear < cbdb.startyear:
	sql = """SELECT c_name_chn
			 	from addresses
			 	where length(c_name_chn) >= 6 and length(c_name_chn) <= %s * 3
				and occurs = 1 and c_firstyear is not null
				and %s < coalesce(earliest_evidence_firstyear, c_firstyear)
		  """ % (settings['MaxGram'], corpus.sample.endyear[sourcefile])
	cursor.execute(sql)
	cbdb_places = set([item[0] for item in cursor.fetchall()])

	###########################################################
	# check types;
	###########################################################

	logging.info("🐍 Checking %s HYDCD words, %s CBDB person names, %s CBDB places for possible older source." % (len(dict_entries), len(cbdb_names), len(cbdb_places)))
	frequencies = CAFrequencies(corpus.name, sourcefile + '.txt', settings, dictionary=dict_entries, relative=False, names=cbdb_names, places=cbdb_places)
	
	if len(frequencies.wordtypes) > 0:
		bar = ShadyBar('Word types. ', max=len(frequencies.wordtypes), width=60)
		for w in frequencies.wordtypes:
			sql = "UPDATE the_words set earliest_evidence_dfz_id = %s where cleanword = '%s'" % (id_external, w)
			cursor.execute(sql)
			counter['wupdate'] += 1
			bar.next()
		bar.finish()
		conn.commit()

	if frequencies.nametypes:
		bar = ShadyBar('Name types. ', max=len(frequencies.nametypes), width=60)
		for n in frequencies.nametypes:
			sql = "UPDATE biog_main set earliest_evidence_dfz_id = %s, earliest_evidence_firstyear = %s where c_name_chn = '%s'" % (id_external, corpus.sample.endyear[sourcefile], n)	
			cursor.execute(sql)
			counter['nupdate'] += 1
			bar.next()
		bar.finish()
		conn.commit()

	if frequencies.placetypes:
		bar = ShadyBar('Place names.', max=len(frequencies.placetypes), width=60)
		for p in frequencies.placetypes:
			sql = "UPDATE addresses set earliest_evidence_dfz_id = %s, earliest_evidence_firstyear = %s where c_name_chn = '%s'" % (id_external, corpus.sample.endyear[sourcefile], p)
			cursor.execute(sql)
			counter['pupdate'] += 1
			bar.next()
		bar.finish()
		conn.commit()

	logging.info("🐍 Updates from %s (%s–%s): %s lexemes, %s names, %s places." % (corpus.sample.dc_title[sourcefile], corpus.sample.startyear[sourcefile], corpus.sample.endyear[sourcefile], len(frequencies.wordtypes), len(frequencies.nametypes), len(frequencies.placetypes)))

logging.info("🐍 Ran %s word type, %s person name, %s place name updates." % (counter['wupdate'], counter['nupdate'], counter['pupdate']))


# need to select the new counts from DB, as we want to output each total count of updated ENTITIES, not the number of executed update statements, would be totally irrelevant
cursor.execute("SELECT count(id) from the_words where earliest_evidence_dfz_id is not NULL")
counter['totalwords'] = cursor.fetchall()[0][0]
cursor.execute("SELECT count(c_personid) from biog_main where earliest_evidence_dfz_id is not NULL")
counter['totalnames'] = cursor.fetchall()[0][0]
cursor.execute("SELECT count(c_addr_id) from addresses where earliest_evidence_dfz_id is not NULL")
counter['totalplaces'] = cursor.fetchall()[0][0]
logging.info("🐍 Whew. Found earlier evidence for %s word types, %s person names, %s place names." % (counter['totalwords'], counter['totalnames'], counter['totalplaces']))

cursor.close()
conn.close()

# control selection
# select w.cleanword, w.pinyin, b.clearbook, b.startyear, b.endyear, db.clearbook, db.startyear, db.endyear from the_words w 
# 	left join the_books b on coalesce(w.earliest_evidence_book_id, w.book_id) = b.id
# 	left join the_books db on w.earliest_evidence_dfz_id = db.id
# 	where earliest_evidence_dfz_id is not null;
# 	
# select c_name_chn, `c_index_year`, `earliest_evidence_firstyear` from biog_main where earliest_evidence_dfz_id is not null;	