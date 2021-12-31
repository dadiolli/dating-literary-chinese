
# -*- coding: utf-8 -*-
settings = {'chronon': 100, 'overlap': 50, 'historystart': -700, 'historyend':1950}
# settings = {'chronon': 50, 'overlap': 25, 'historystart': 1450, 'historyend':1925}

###########################################################
# load stuff and get prepared
###########################################################

from modules.initialize_logger3 import *
from modules.toolbox3 import database_connect
from modules.dynasties3 import chronon_dict, hydcd_dynasties
from collections import Counter
from mafan import tradify
from progress.bar import ShadyBar
import argparse, glob, numpy as np, os, pandas as pd, regex as re, sys, time

initialize_logger("corpus_builder.log")

###########################################################
# Grab command line arguments
###########################################################

parser = argparse.ArgumentParser(description='Build chronon corpus.')
parser.add_argument('-b', '--build', help='(Re-)build Corpus.)', action="store_true")
args, do = parser.parse_args(), []

###########################################################
# Other options
###########################################################

excluded_books = []
# excluded_books = ['史记', '汉书', '三国志', '後汉书', '宋书', '南齐书', '魏书', '梁书', '陈书', '北齐书', '周书', '隋书', '晋书', '南史', '北史', '旧唐书', '旧五代史', '新五代史', '新唐书', '宋史', '金史', '辽史', '元史', '明史', '清史稿']
chrononpath = "models/chronons_allquotes/"
# chrononpath = "models/chronons_nozhengshi"

###########################################################
# Build chronons
###########################################################

if args.build:
	conn, cursor = database_connect()
	chronons = {}
	for c in range(settings['historystart'], settings['historyend'], settings['overlap']):
		chronons[c] = ''
	# print(sorted(chronons))

	for i, c in enumerate(sorted(chronons)):
		c_start, c_end = c, c + settings['chronon']
		
		# get relevant IDs from the_books
		sql_get_books = """select id, clearbook from the_books where ((startyear >= %s and startyear <= %s) or 
						  (startyear <= %s and endyear >= %s)) and usecount > 1""" % (c_start, c_end, c_start, c_end)
		if len(excluded_books) > 0:
			sql_get_books += " and clearbook not in ('" + "','".join(excluded_books) + "')" 

		cursor.execute(sql_get_books)
		books = {k:v for k,v in cursor.fetchall()}
		logging.info("📕 " + str(cursor.rowcount) + ' sources used in chronon %s–%s (%s of %s).' % (c_start, c_end, i, len(chronons)))
					  
		# load relevant entries via the_citations
		sql_get_entries = """select id, entry from hydcd_words where id in (select word_id 
							 from the_citations where book_id in (""" + ','.join([str(k) for k in books]) + "))" 
		cursor.execute(sql_get_entries)
		entries = {k:v for k,v in cursor.fetchall()}
		logging.info("🐍 Got " + str(cursor.rowcount) + ' entries used in chronon %s–%s.' % (c_start, c_end))
		
		# list of quotes will provide the to-do-list here
		sql_get_citations = """select word_id, book_id from the_citations where 
							   book_id in (""" + ','.join([str(k) for k in books]) + ") order by word_id" 
		cursor.execute(sql_get_citations)
		citationlist = [(w, b) for w, b in cursor.fetchall()]
		logging.info("🐍 Selected " + str(cursor.rowcount) + ' citations within these entries,...')

		# regex out the citations between “ and ” chars and add to chronon
		bar = ShadyBar('Building.', max=len(citationlist), width=60)
		
		for word_id, book_id in citationlist:
			citations = re.findall('《' + books[book_id] + '[^》]*[^《“]*》：?“([^”]*)”', entries[word_id])
			# only suitable entries《书》：“今予惟龔行天之罰。”, some have missing ：, some have chapter 《左传·僖公二十三年》：“及齊，...
			# demo: 《书[^》]*[^《“]*》：?“([^”]*)” -> Full match	32-47	《书》：“今予惟龔行天之罰。”, Group 1.	37-46	今予惟龔行天之罰。
			# chronons[c] += "\n::::::" + str(word_id) + " - " + books[book_id] + "::::::\n" + "\n".join(set(citations))
			chronons[c] += "\n".join(set(citations))
			bar.next()
		bar.finish()
		# print(chronons[c])

		# save out the chronon file txt
		with open(chrononpath + "/" + str(c) + ".txt", "w") as f: 
			f.write(chronons[c]) 
	cursor.close(); conn.close()