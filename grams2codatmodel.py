"""
(Re-)Build a document level corpus from CrossAsia n-Gram files.
Calculate TF-IDF optionally.
Set first and last chronon, text count of each chronon.

Use different interpolation/smoothing approaches on the model, such as neighbouring
chronons as suggested by Kumar2013, or lowest / mean neighbour (Kanhabua2008a),
or try Laplace / add one smoothing.

Use parser arguments.
"""

# set chronons suitable for the corpus
settings = {'Chronon': 50, 
			'Overlap': 25, 
			'HistoryStart': 1475, 
			'HistoryEnd': 1900, 
			'Even': False, 
			'ChrononSize': 50,# 2, # 50, #40
			'LookupMinimumNgramCount': 1, # minimum absolute token frequency for consideration
			'MinGram': 1,
			'MaxGram': 2,
			'Punctuation': False,
			'OriginalCorpus': 'hydcd/chronons_xxskqs_12_times_norm_old', # use this corpus for text selection
			# 'OriginalCorpus': 'hydcd/chronons_difangzhi_12', # use this corpus for text selection
			'UseCBDB': True,
			'UseCBDBPlaces': False,
			'UseTimeExpr': True,
			'HYDCDStandardize': True,
			'SmoothingMethod': False, # 'laplace' # 'neighbour'
			'ModelType': 'chronon'
			}

 # laplace_lambda = 0.5

###########################################################
# load stuff and get prepared
###########################################################

from modules.classes3 import CAFrequencies, CAGrams, Dictionary
from modules.dynasties3 import chronon_dict
from modules.initialize_logger3 import *
from modules.toolbox3 import term_frequency 

from mafan import tradify
from progress.bar import ShadyBar
import argparse, gc, glob, json, multiprocessing, numpy as np, os, pandas as pd, regex as re, sys, time

multiprocessing.set_start_method('fork')
###########################################################
# Grab command line arguments
###########################################################
parser = argparse.ArgumentParser(description='Build chronon corpus.')
parser.add_argument('-w', '--words', help='(Re-)count chronon word frequencies.', action="store_true", default=True)
parser.add_argument('-n', '--grams', help='(Re-)count chronon n-gram frequencies.', action="store_true", default=False)
parser.add_argument('-t', '--tfidf', help='(Re-)calculate TF-IDF', action="store_true")
parser.add_argument('-e', '--entropy', help='(Re-)calculate Temporal entropy', action="store_true")
parser.add_argument('-s', '--smoothing', help='Use lowest neighbour (s)moothing', action="store_true")

args, do = parser.parse_args(), []
if args.words: do.append('words')
if args.grams: do.append('grams')
###########################################################
# Other options
###########################################################

# corpus = CAGrams('difangzhi-grams', 'difangzhi-metadata.xlsx', minchronon = settings['HistoryStart'])
# corpuspath = 'primary_sources/difangzhi-grams'
corpus = CAGrams('xx-skqs-grams', 'xuxiu_metadata_year.xlsx', minchronon = settings['HistoryStart'])
corpuspath = 'primary_sources/xx-skqs-grams'
chrononpath = "hydcd/chronons_xxskqs_12_times_norm"
try:
	os.makedirs(chrononpath)
except:
	pass
initialize_logger("corpus_builder.log", logpath=chrononpath)
logging.info("🐍 Building %s chronon model in %s with %s-%s char %s and minimum lookup of %s." % (corpus.name, chrononpath, settings['MinGram'], settings['MaxGram'], do, settings['LookupMinimumNgramCount']))
logging.info("🐍 Using CBCB person names: %s, place names: %s, time expressions %s." % (settings['UseCBDB'], settings['UseCBDBPlaces'], settings['UseTimeExpr']))


results, chronons, totals = dict(), dict(), dict()
for c in range(settings['HistoryStart'], settings['HistoryEnd'], settings['Overlap']):
	chronons[c] = c

if 'words' in do:
	print("🐼 Loading dictionary...", end="\r")	
	dictionary = Dictionary(settings, full=True)
	logging.info("📚 Maximum possible dimensions: %s." % len(dictionary.alltypes()))

def chronon_counts(c):
	c_start, c_end = c, c + settings['Chronon']
	# get settings['ChrononSize'] suitable books from the corpus
	assert len(corpus.metadata.loc[(corpus.metadata['startyear'] >= c_start) & (corpus.metadata['endyear'] <= c_end)]) >= settings['ChrononSize'], "❎ Not enough data for chronon %s" % (c)
	if 'OriginalCorpus' in settings:
		current_chronon_meta = pd.read_csv(settings['OriginalCorpus'] + '/meta' + str(c) + '.csv', index_col='dc_identifier')
	else:
		current_chronon_meta = corpus.metadata.loc[(corpus.metadata['startyear'] >= c_start) & (corpus.metadata['endyear'] <= c_end)].sample(settings['ChrononSize'])
	current_chronon_meta.to_csv(chrononpath + '/' + 'meta' + str(c_start) + '.csv', encoding='utf-8', index=True, float_format='%.8f')
	
	print("🐼 Got %s texts for chronon %s–%s... (of %s)          " % (len(current_chronon_meta), c_start, c_end, len(chronons)), end="\r")
	# get freqs for each book
	chronontexts = []
	for i, text_id in enumerate(current_chronon_meta.index):
		print("🐼 Loading frequencies for text %s in chronon %s–%s...           " % (current_chronon_meta.dc_title[text_id], c_start, c_end), end="\r")
		current_freqs = CAFrequencies(corpus.name, text_id + '.txt', settings, dictionary=False, relative=False)
		# current_freqs = CAFrequencies(corpus.name, text_id + '.txt', settings, dictionary=dictionary.alltypes(), relative=False)		
		if 'grams' not in do: 
			# current_text = pd.DataFrame.from_dict(current_freqs.wordsfreq_dict, orient='index', columns=['tokens'])
			current_text = current_freqs.freq_frame[current_freqs.freq_frame.index.isin(dictionary.alltypes_as_index())].copy()
		else:
			current_text = current_freqs.freq_frame.copy()
		current_text.index.name = 'item'
		current_text['text'] = text_id
		current_text = current_text.set_index([current_text.index, 'text'])
		
	# chronontotals = pd.DataFrame(pd.concat(chronontexts))
	# chronontotals = pd.DataFrame(pd.concat(chronontexts)[['tokens']].groupby(level='item').sum())
	# if args.smoothing and settings['SmoothingMethod'] == 'laplace':
	#	chronontotals['tokens'] = chronontotals.tokens.astype(float)
	#	chronontotals['tokens'] += laplace_lambda

	# del current_text, current_freqs, chronontexts
	# gc.collect()
	# chronontotals = chronontotals[chronontotals.tokens > 1] # not a good idea, unfortunately...	
		print("🐼 Calculated token counts for text %s (%s) chronon %s–%s... (of %s)" % (text_id, current_chronon_meta.dc_title[text_id], c_start, c_end, len(chronons)), end="\r")
		gramstokencount = current_text.tokens.sum()
		gramstokenmax = current_text.tokens.max()
		vocsize = len(current_text.index)
		print("🐼 Calculating frequencies for text %s (%s) in chronon %s–%s... (of %s)" % (text_id, current_chronon_meta.dc_title[text_id], c_start, c_end, len(chronons)), end="\r")
		current_text['freq'] = current_text.apply(lambda row: term_frequency(row.tokens, gramstokencount, gramstokenmax, vocsize), axis=1)
		current_text['documents'], current_text['chronon'] = 1, c
		current_text['documents'] = current_text['documents'].astype('int8')
		current_text['chronon'] = current_text['chronon'].astype('int16')
		chronontexts.append(current_text)
		chronontexts_frame = pd.DataFrame(pd.concat(chronontexts))
	gc.collect()
	return chronontexts_frame


###########################################################
# Build chronons and create counts
###########################################################

pool = multiprocessing.Pool(multiprocessing.cpu_count()-3)
poolresults = pool.map(chronon_counts, chronons)
pool.close()
results['grams'] = pd.concat(poolresults)
del poolresults
gc.collect()
	
os.chdir(chrononpath)
with open('settings.json', 'w') as storage:
    json.dump(settings, storage)
chronon_amount = len(chronons)
unique_document_amount = len(results['grams'].index.get_level_values(1).unique())
document_amount = settings['ChrononSize'] * chronon_amount

###########################################################
# do general transformations on the dataframe
###########################################################

if 'words' in do:
	if 'grams' in do: 
		print("🐼 Extracting word dimensions...", end="\r")	
		# form single index data frame to speed up intersection
		# results_singdex = results['grams'].copy(deep=True).reset_index(level=[0,1])		
		# words = pd.DataFrame(results_singdex.item.isin(dictionary.alltypes_as_index()))
		# results['words'] = results_singdex.iloc[words.loc[words.item == True].index].set_index(['item', 'chronon'])
		results['words'] = results['grams']
	else:
		results['words'] = results['grams']

limit = {'grams': None, 'words': None}
for listtype in do:
	if settings['Even']:
		print("🐼 Getting maximum %s dimensions..." % (listtype), end="\r")	
		limit[listtype] = results[listtype].groupby(level='text').size().min()
		print("🐼 Using %s %s dimensions..." % (limit[listtype], listtype), end="\r")
		### use limits in Export!!

	# create totals
	print("🐼 Creating %s totals..." % (listtype), end="\r")
	totals[listtype] = pd.DataFrame(data=results[listtype][['tokens', 'documents']].groupby(level='item').sum())
	if args.entropy:
		# totals[listtype]['te-prep'] = 0
		totals[listtype]['te-preprel'] = 0
	totaltokencount = totals[listtype]['tokens'].sum()
	print("🐼 Calculating %s totals relative frequencies..." % (listtype), end="\r")
	totals[listtype]['freq'] = totals[listtype]['tokens'] / totaltokencount

	# join the document frequencies
	if args.tfidf:
		print("🐼 Getting %s document frequencies..." % (listtype), end="\r") 
		totals[listtype].rename(columns = {'documents':'df'}, inplace = True) 
		results[listtype] = results[listtype].join(totals[listtype][['df']])
		print("🐼 Calculating %s TF-IDF...          " % (listtype), end="\r") 
		results[listtype]['idf'] = results[listtype].apply(lambda row: np.log2(float(chronon_amount) / row['df']), axis=1)
		results[listtype]['tfidf'] = results[listtype].apply(lambda row: row['freq'] * row['idf'], axis=1)

	temp = {}
	training_documents = results['grams'].index.get_level_values(1).unique()

	for i, doc in enumerate(training_documents):		
		freqlist_filename, even_freqlist_filename = "freq" + listtype + "_" + str(doc) + ".csv", "even_freq" + listtype + "_" + str(doc) + ".csv"
		print("🐼 Saving %s frequency data for document %s (%s of %s)..." % (listtype, doc, i+1, unique_document_amount), end="\r")
		current_document_data = results[listtype].xs(doc, level='text').copy(deep=True)
		# if there are duplicate documents in the corpus due to its chronon nature, we should drop them from the counts
		current_document_earliest_chronon = current_document_data.chronon.min()
		current_document_data = current_document_data[current_document_data.chronon == current_document_earliest_chronon]

		if args.smoothing:
			# if settings['SmoothingMethod'] == 'neighbour':
			# 	previous_chronon = settings['HistoryStart'] if chronon == settings['HistoryStart'] else chronon - settings['Overlap']
			# 	next_chronon = chronon if chronon == settings['HistoryEnd'] - settings['Overlap'] else chronon + settings['Overlap']
			# 	print("Current chronon is %s: %s used as previous, %s used as next." % (chronon, previous_chronon, next_chronon), end='\r')

			# 	previous_loader = results[listtype].xs(previous_chronon, level='chronon').copy(deep=True)
			# 	next_loader = results[listtype].xs(next_chronon, level='chronon').copy(deep=True)
			# 	neighbours = previous_loader.append(next_loader, ignore_index=False, sort=False).sort_values('freq',ascending=False)
			# 	# neighbours = neighbours[~neighbours.index.duplicated(keep='last')] # keep row with lowest freq
			# 	neighbours = neighbours.groupby(neighbours.index).mean()
			# 	# neighbours = neighbours.groupby(neighbours.index).min()
			# 	use_neighbours = neighbours[~neighbours.index.isin(current_document_data.index)]
			# 	totals[listtype]['tokens'].add(use_neighbours['tokens'], axis='index', fill_value=0) # !!!
			# 	current_document_data = current_document_data.append(use_neighbours, ignore_index=False, sort=False)
			
			if settings['SmoothingMethod'] == 'laplace':
				totals[listtype]['tokens'] = totals[listtype]['tokens'].astype(float)
				unknown_words = totals[listtype][~totals[listtype].index.isin(current_document_data.index)].index
				add_unknown = pd.DataFrame(columns=['tokens'], data=laplace_lambda, index=unknown_words)
				
				# totals[listtype].loc[totals[listtype].index.isin(add_unknown.index), 'tokens'] += laplace_lambda
				# totals[listtype]['tokens'][totals[listtype].index.isin(add_unknown.index)] += laplace_lambda
				totals[listtype]['tokens'].add(add_unknown['tokens'], axis='index', fill_value=0)

				current_document_data['tokens'] = current_document_data.tokens.astype('float')
				current_document_data['tokens'] += laplace_lambda
				current_document_data = current_document_data.append(add_unknown, ignore_index=False, sort=False)

		
		# need to recalculate relative frequencies
		totaltokens = current_document_data['tokens'].sum()
		maxtokens = current_document_data['tokens'].max()
		vocsize = len(current_document_data.index)
		print("🐼 Recalculating %s frequencies for document %s (%s of %s)..." % (listtype, doc, i+1, document_amount), end="\r")
		current_document_data['freq'] = current_document_data.apply(lambda row: term_frequency(row.tokens, totaltokens, maxtokens, vocsize), axis=1)

		temp[doc] = current_document_data

		# export chronon lines according to limit, (= all if None)
		# current_document_data['tokens'] = current_document_data.tokens.astype('int64')
		
		# drop unnecessary columns
		current_document_data = current_document_data.reset_index().set_index('item')
		current_document_data.drop(['documents'], axis=1, inplace=True)

		if settings['Even']:
			current_document_data.sort_values(by='tokens', ascending=False).iloc[0:limit[listtype]].to_csv(even_freqlist_filename, encoding='utf-8', index=True, float_format='%.8f')
		# always do the full export as well
		current_document_data.sort_values(by='tokens', ascending=False).to_csv(freqlist_filename, encoding='utf-8', index=True, float_format='%.8f')
		gc.collect()

	# need to recalculate total freqs!
	if args.smoothing:
		print("🐼 Recalculating %s total frequencies... to fit smoothing." % (listtype), end="\r") 
		totaltokencount = totals[listtype]['tokens'].sum()
		totalmaxtokens = totals[listtype]['tokens'].max()
		vocsize = len(totals[listtype]['tokens'].index)
		totals[listtype]['freq'] = totals[listtype].apply(lambda row: term_frequency(row.tokens, totaltokens, maxtokens, vocsize), axis=1)

	# for i, chronon in enumerate(chronons):
	# 	print("🐼 Manipulating %s frequency data for chronon %s (%s of %s)..." % (listtype, chronon, i+1, chronon_amount), end="\r")
	# 	if args.entropy:
	# 		print("🐼 Calculating %s temporal entropy for chronon %s of %s (%s).  " % (listtype, i+1, chronon_amount, chronon), end="\r")
	# 		# term freq in doc / (sum of all termfreq in all doc)
	# 		# temp[chronon]['te-prep'] = temp[chronon].apply(lambda row: (row['tokens'] / float(totals[listtype]['tokens'][row.name])) * np.log2(float(row['tokens']) / totals[listtype]['tokens'][row.name]), axis=1)
	# 		# totals[listtype]['te-prep'] = totals[listtype]['te-prep'].add(temp[chronon]['te-prep'], axis='index', fill_value=0)		
	# 		temp[chronon]['te-preprel'] = temp[chronon].apply(lambda row: (row['freq'] / float(totals[listtype]['freq'][row.name])) * np.log2(float(row['freq']) / totals[listtype]['freq'][row.name]), axis=1)
	# 		totals[listtype]['te-preprel'] = totals[listtype]['te-preprel'].add(temp[chronon]['te-preprel'], axis='index', fill_value=0)		

	# if args.entropy:
	#	print("🐼 Calculating %s temporal entropy." % (listtype), end="\r") 
		# totals[listtype]['te'] = totals[listtype].apply(lambda row: 1 + ((1 / np.log2(float(chronon_amount))) * row['te-prep']), axis=1)
	totals[listtype]['terel'] = 0
	# export totals
	totals[listtype].to_csv(listtype + 'totals.csv', encoding='utf-8', index=True, float_format='%.8f')
	gc.collect()

print("\n\a\a")
exit()