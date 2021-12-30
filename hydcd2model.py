"""
(Re-)Build a chronon corpus from HYDCD quotations.
The original text files need to be generated from --build routine
of hydcd2corpus.py

Otherwise this is identical to grams2model_smoothed.py

Calculate TF-IDF and temporal entropy optionally.
Set first and last chronon, text count of each chronon.

Use different interpolation/smoothing approaches on the model, such as neighbouring
chronons as suggested by Kumar2013, or lowest / mean neighbour (Kanhabua2008a),
or try Laplace / add one smoothing.
"""

# set chronons suitable for the corpus
settings = {'Chronon': 100, 
			'Overlap': 50, 
			'HistoryStart': -700, 
			'HistoryEnd': 1950, 
			'Even': True, 
#			'ChrononSize': 50, #40
			'LookupMinimumNgramCount': 1, # minimum absolute token frequency for consideration
			'MinGram': 1,
			'MaxGram': 2,
			'Punctuation': False,
#			'OriginalCorpus': 'hydcd/chronons_difangzhi_12', # use this corpus for text selection
			'UseCBDB': False,
			'UseCBDBPlaces': False,
			'UseTimeExpr': True,
			'HYDCDStandardize': False,
			'SmoothingMethod': False # 'laplace' # 'neighbour'
			}

 # laplace_lambda = 0.5

###########################################################
# load stuff and get prepared
###########################################################

from modules.classes3 import Dictionary, ResearchText, TextFrequencies
from modules.dynasties3 import chronon_dict
from modules.initialize_logger3 import *
from modules.toolbox3 import term_frequency 

from mafan import tradify
import argparse, gc, glob, multiprocessing, numpy as np, os, pandas as pd, regex as re, sys, time

multiprocessing.set_start_method('fork')
###########################################################
# Grab command line arguments
###########################################################
parser = argparse.ArgumentParser(description='Build chronon corpus.')
parser.add_argument('-b', '--build', help='(Re-)build Corpus.)', action="store_true")
parser.add_argument('-w', '--words', help='(Re-)count chronon word frequencies.', action="store_true", default=True)
parser.add_argument('-n', '--grams', help='(Re-)count chronon n-gram frequencies.', action="store_true", default=False)
parser.add_argument('-t', '--tfidf', help='(Re-)calculate TF-IDF', action="store_true")
parser.add_argument('-e', '--entropy', help='(Re-)calculate Temporal entropy', action="store_true")
parser.add_argument('-s', '--smoothing', help='Use lowest neighbour (s)moothing', action="store_true", default=False)

args, do = parser.parse_args(), []
if args.words: do.append('words')
if args.grams: do.append('grams')
###########################################################
# Other options
###########################################################

chrononpath = "hydcd/chronons_allquotes_12"
corpuspath = 'hydcd/chronons_allquotes'

try:
	os.makedirs(chrononpath)
except:
	pass
initialize_logger("corpus_builder.log", logpath=chrononpath)
logging.info("🐍 Building %s chronon model in %s with %s-%s char %s and minimum lookup of %s." % ('HYDCD', chrononpath, settings['MinGram'], settings['MaxGram'], do, settings['LookupMinimumNgramCount']))
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
	chronon_file =  open(corpuspath + '/' + str(c) + '.txt')
	chronon_content = ResearchText(chronon_file, punctuation=settings['Punctuation'], tradify=True)
	frequencies = TextFrequencies(chronon_content, settings, verbose=False)
	print("🐍 Computed frequencies for chronon %s (of %s)..." % (c, len(chronons)), end="\r")
	
	chronontotals = pd.DataFrame.from_dict(frequencies.freq_dict, orient='index', columns=['tokens'])
	chronontotals.index.name = 'item'
	chronontotals['chronons'], chronontotals['chronon'] = 1, c
	
	if 'grams' not in do: 
		chronontotals = chronontotals[chronontotals.index.isin(dictionary.alltypes_as_index())]

	if args.smoothing and settings['SmoothingMethod'] == 'laplace':
		chronontotals['tokens'] = chronontotals.tokens.astype(float)
		chronontotals['tokens'] += laplace_lambda

	vocsize = len(chronontotals.index)
	gramstokencount = chronontotals.tokens.sum()
	gramstokenmax = chronontotals.tokens.max()
	print("🐼 Calculating frequencies for chronon %s–%s... (of %s)" % (c_start, c_end, len(chronons)), end="\r")
	chronontotals['freq'] = chronontotals.apply(lambda row: term_frequency(row.tokens, gramstokencount, gramstokenmax, vocsize), axis=1)
	
	chronontotals['chronons'] = chronontotals['chronons'].astype('int8')
	chronontotals['chronon'] = chronontotals['chronon'].astype('int16')
	chronontotals = chronontotals.set_index([chronontotals.index, 'chronon'])
	gc.collect()
	return chronontotals


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
chronon_amount = len(chronons)

###########################################################
# do general transformations on the dataframe
###########################################################

if 'words' in do:
	if 'grams' in do: 
		print("🐼 Extracting word dimensions...", end="\r")	
		# form single index data frame to speed up intersection
		results_singdex = results['grams'].copy(deep=True).reset_index(level=[0,1])
		words = pd.DataFrame(results_singdex.item.isin(dictionary.alltypes_as_index()))
		results['words'] = results_singdex.iloc[words.loc[words.item == True].index].set_index(['item', 'chronon'])
	else:
		results['words'] = results['grams']

limit = {'grams': None, 'words': None}
for listtype in do:
	if settings['Even']:
		print("🐼 Getting maximum %s dimensions..." % (listtype), end="\r")	
		limit[listtype] = results[listtype].groupby(level='chronon').size().min()
		print("🐼 Using %s %s dimensions..." % (limit[listtype], listtype), end="\r")
		### use limits in Export!!

	# create totals
	print("🐼 Creating %s totals..." % (listtype), end="\r")
	totals[listtype] = pd.DataFrame(data=results[listtype][['tokens', 'chronons']].groupby(level='item').sum())
	if args.entropy:
		# totals[listtype]['te-prep'] = 0
		totals[listtype]['te-preprel'] = 0
	totaltokencount = totals[listtype]['tokens'].sum()
	print("🐼 Calculating %s totals relative frequencies..." % (listtype), end="\r")
	totals[listtype]['freq'] = totals[listtype]['tokens'] / totaltokencount

	# join the document frequencies
	if args.tfidf:
		print("🐼 Getting %s document frequencies..." % (listtype), end="\r") 
		totals[listtype].rename(columns = {'chronons':'df'}, inplace = True) 
		results[listtype] = results[listtype].join(totals[listtype][['df']])
		print("🐼 Calculating %s TF-IDF...          " % (listtype), end="\r") 
		results[listtype]['tfidf'] = results[listtype].apply(lambda row: row['freq'] * (np.log2(float(chronon_amount) / row['df'])), axis=1)

	temp = {}

	for i, chronon in enumerate(chronons):		
		freqlist_filename, even_freqlist_filename = "freq" + listtype + "_" + str(chronon) + ".csv", "even_freq" + listtype + "_" + str(chronon) + ".csv"
		print("🐼 Saving %s frequency data for chronon %s (%s of %s)..." % (listtype, chronon, i+1, chronon_amount), end="\r")
		current_chronon_data = results[listtype].xs(chronon, level='chronon').copy(deep=True)

		if args.smoothing:
			if settings['SmoothingMethod'] == 'neighbour':
				previous_chronon = settings['HistoryStart'] if chronon == settings['HistoryStart'] else chronon - settings['Overlap']
				next_chronon = chronon if chronon == settings['HistoryEnd'] - settings['Overlap'] else chronon + settings['Overlap']
				print("Current chronon is %s: %s used as previous, %s used as next." % (chronon, previous_chronon, next_chronon), end='\r')

				previous_loader = results[listtype].xs(previous_chronon, level='chronon').copy(deep=True)
				next_loader = results[listtype].xs(next_chronon, level='chronon').copy(deep=True)
				neighbours = previous_loader.append(next_loader, ignore_index=False, sort=False).sort_values('freq',ascending=False)
				# neighbours = neighbours[~neighbours.index.duplicated(keep='last')] # keep row with lowest freq
				neighbours = neighbours.groupby(neighbours.index).mean()
				# neighbours = neighbours.groupby(neighbours.index).min()
				use_neighbours = neighbours[~neighbours.index.isin(current_chronon_data.index)]
				totals[listtype]['tokens'].add(use_neighbours['tokens'], axis='index', fill_value=0) # !!!
				current_chronon_data = current_chronon_data.append(use_neighbours, ignore_index=False, sort=False)
			
			elif settings['SmoothingMethod'] == 'laplace':
				totals[listtype]['tokens'] = totals[listtype]['tokens'].astype(float)
				unknown_words = totals[listtype][~totals[listtype].index.isin(current_chronon_data.index)].index
				add_unknown = pd.DataFrame(columns=['tokens'], data=laplace_lambda, index=unknown_words)
				
				# totals[listtype].loc[totals[listtype].index.isin(add_unknown.index), 'tokens'] += laplace_lambda
				# totals[listtype]['tokens'][totals[listtype].index.isin(add_unknown.index)] += laplace_lambda
				totals[listtype]['tokens'].add(add_unknown['tokens'], axis='index', fill_value=0)

				current_chronon_data['tokens'] = current_chronon_data.tokens.astype('float')
				current_chronon_data['tokens'] += laplace_lambda
				current_chronon_data = current_chronon_data.append(add_unknown, ignore_index=False, sort=False)

		
		# need to recalculate relative frequencies
		totaltokens = current_chronon_data['tokens'].sum()
		maxtokens = current_chronon_data['tokens'].max()
		vocsize = len(current_chronon_data.index)
		print("🐼 Recalculating %s frequencies for chronon %s (%s of %s)..." % (listtype, chronon, i+1, chronon_amount), end="\r")
		current_chronon_data['freq'] = current_chronon_data.apply(lambda row: term_frequency(row.tokens, totaltokens, maxtokens, vocsize), axis=1)

		temp[chronon] = current_chronon_data

		# export chronon lines according to limit, (= all if None)
		# current_chronon_data['tokens'] = current_chronon_data.tokens.astype('int64')
		if settings['Even']:
			current_chronon_data.sort_values(by='tokens', ascending=False).iloc[0:limit[listtype]].to_csv(even_freqlist_filename, encoding='utf-8', index=True, float_format='%.8f')
		# always do the full export as well
		current_chronon_data.sort_values(by='tokens', ascending=False).to_csv(freqlist_filename, encoding='utf-8', index=True, float_format='%.8f')
		gc.collect()

	# need to recalculate total freqs!
	if args.smoothing:
		print("🐼 Recalculating %s total frequencies... to fit smoothing." % (listtype), end="\r") 
		totaltokencount = totals[listtype]['tokens'].sum()
		totalmaxtokens = totals[listtype]['tokens'].max()
		vocsize = len(totals[listtype]['tokens'].index)
		totals[listtype]['freq'] = totals[listtype].apply(lambda row: term_frequency(row.tokens, totaltokens, maxtokens, vocsize), axis=1)

	for i, chronon in enumerate(chronons):
		print("🐼 Manipulating %s frequency data for chronon %s (%s of %s)..." % (listtype, chronon, i+1, chronon_amount), end="\r")
		if args.entropy:
			print("🐼 Calculating %s temporal entropy for chronon %s of %s (%s).  " % (listtype, i+1, chronon_amount, chronon), end="\r")
			# term freq in doc / (sum of all termfreq in all doc)
			# temp[chronon]['te-prep'] = temp[chronon].apply(lambda row: (row['tokens'] / float(totals[listtype]['tokens'][row.name])) * np.log2(float(row['tokens']) / totals[listtype]['tokens'][row.name]), axis=1)
			# totals[listtype]['te-prep'] = totals[listtype]['te-prep'].add(temp[chronon]['te-prep'], axis='index', fill_value=0)		
			temp[chronon]['te-preprel'] = temp[chronon].apply(lambda row: (row['freq'] / float(totals[listtype]['freq'][row.name])) * np.log2(float(row['freq']) / totals[listtype]['freq'][row.name]), axis=1)
			totals[listtype]['te-preprel'] = totals[listtype]['te-preprel'].add(temp[chronon]['te-preprel'], axis='index', fill_value=0)		

	if args.entropy:
		print("🐼 Calculating %s temporal entropy." % (listtype), end="\r") 
		# totals[listtype]['te'] = totals[listtype].apply(lambda row: 1 + ((1 / np.log2(float(chronon_amount))) * row['te-prep']), axis=1)
		totals[listtype]['terel'] = totals[listtype].apply(lambda row: 1 + ((1 / np.log2(float(chronon_amount))) * row['te-preprel']), axis=1)
	# export totals
	totals[listtype].to_csv(listtype + 'totals.csv', encoding='utf-8', index=True, float_format='%.8f')
	gc.collect()

print("\n\a\a")
exit()