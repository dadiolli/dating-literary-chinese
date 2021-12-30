###########################################################
# Import external modules
###########################################################

import logging, math, pandas as pd, regex as re, sys
from collections import Counter, defaultdict
from datetime import datetime
from itertools import starmap
from progress.bar import ShadyBar

###########################################################
# Import own modules
###########################################################

from modules.classes3 import CAFrequencies, CAGrams, CBDBPerson, HYDCDWord, PlainTextCorpus, ResearchText, TextFrequencies, TimeMatch
from modules.chronon_dating import multichron
from modules.dynasties3 import century_dict, century_profile_df, get_chronon_for_year
from modules.toolbox3 import database_connect, regex_builder, select_builder, select_builder_cbdb, grams_regex_builder

def neologism_profiler_grams(sourcefile, settings, corpus=None, current_part=0, observations=False):
	"Do neologism profiling on a CrossAsia ngram resource or an input text"
	
	# load suitable HYDCD info		
	hydcd_profile = pd.read_csv('hydcd/profile_' + 'NonHYDCD_' + str(settings['UseNonHYDCDEvidence']) + '_UseDFZ_' + str(settings['UseDFZTraining']) + '_Min_' + str(settings['MinGram']) + '_Max_' + str(settings['MaxGram']) + "__predict_piotrowski.csv", index_col="century")
	# hydcd_profile = pd.read_csv('hydcd/profile_' + 'NonHYDCD_' + str(settings['UseNonHYDCDEvidence']) + '_UseDFZ_' + str(settings['UseDFZTraining']) + '_Min_' + str(settings['MinGram']) + '_Max_' + str(settings['MaxGram']) + ".csv", index_col="century")
	dict_words = open('hydcd/wordlist_punctuation_false.txt', 'r') # get word list from file (faster than db)
	dict_entries = set(dict_words.read().split('\n'))
	typesorts, alltypes = [], {}

	if settings['UseCBDB']:
		cbdb_names = open('hydcd/cbdb_unique_names.txt', 'r') # get word list from file (faster than db)
		cbdb_names = set(cbdb_names.read().split('\n'))
		typesorts.append('names')
	else:
		cbdb_names = False
	
	if settings['UseCBDBPlaces']:
		cbdb_places = open('hydcd/cbdb_unique_places.txt', 'r') # get word list from file (faster than db)
		cbdb_places = set(cbdb_places.read().split('\n'))
		typesorts.append('places')
	else:
		cbdb_places = False

	#################################################
	# get the file from the corpus, or use the given file
	#################################################

	if corpus: 
		if isinstance(corpus, CAGrams): # this CrossAsia ngrams
			f = CAFrequencies(corpus.name, sourcefile + '.txt', settings, dictionary=dict_entries, relative=True, names=cbdb_names, places=cbdb_places)
		elif isinstance(corpus, PlainTextCorpus):
			file = open(corpus.path + '/' + sourcefile)
			source = ResearchText(file, settings['Punctuation'], settings['Split'], tradify=True)
			f = TextFrequencies(source, settings, index = current_part, dictionary=dict_entries, relative=True, name=source.filename, names=cbdb_names, places=cbdb_places)
	else:
		f = TextFrequencies(sourcefile, settings, index = current_part, dictionary=dict_entries, relative=True, name=sourcefile.filename, names=cbdb_names, places=cbdb_places)
	logging.info("Checking %s n-grams appearing %s or more times in the input text against %s entries in the dictionary." % (len(f.gramstypes), settings['LookupMinimumNgramCount'], len(dict_entries)))	

	words = f.wordtypes # intersect
	logging.info("Of %s n-grams, %s were found to be 漢語大詞典 words." % (len(f.gramstypes), len(words)))

	conn, cursor = database_connect()

	#################################################
	# load temporal information for lexemes
	#################################################

	if settings['ExcludeSelf']: # exclude a given text 
		try: 
			texthydcdname = observations.ix[(text.filename, current_part), 'hydcd_name']
			logging.info("🐼 Text is cited in HYDCD as %s." % (texthydcdname))
			sql = select_builder(words, settings, texthydcdname)
		except:
			logging.info("❌ No HYDCD usage information on the input text %s. " % (text.filename))
			sql = select_builder(words, settings)
	else:
		sql = select_builder(words, settings)
	logging.debug(sql)

	logging.info('Loading dictionary entries...') # use HYDCD words
	cursor.execute(sql)
	word_sources = list(starmap(HYDCDWord, cursor.fetchall()))
	logging.info(str(cursor.rowcount) + ' corresponding dictionary entries with citation and year were retrieved from the database.')

	profile, dynastywordlist, bookwordlist, counter = profile_worker(word_sources, settings, f, prfltype='words')
	profile['smoothed'] = hydcd_profile['weight'] * profile['count']
	profile['piotrowskismoothed'] = hydcd_profile['piotweight'] * profile['count']

	# prepare AYL calculations
	for c, row in profile.iterrows():
		counter['smoothedsum'] += profile.at[c,'count'] * hydcd_profile.at[c,'weight'] * (c+50)
		counter['smoothedwords'] += profile.at[c,'count'] * hydcd_profile.at[c,'weight']
		counter['piotsmoothedsum'] += profile.at[c,'count'] * hydcd_profile.at[c,'piotweight'] * (c+50)
		counter['piotsmoothedwords'] += profile.at[c,'count'] * hydcd_profile.at[c,'piotweight']		

	# print some output if so desired
	detailed_output(word_sources, settings, text=sourcefile)

	#################################################
	# load temporal information for names and places
	#################################################

	for typesort in typesorts:
		sql = select_builder_cbdb(f.alltypes[typesort], settings, ner=typesort)
		logging.info('Getting %s entities...' % (typesort))
		cursor.execute(sql)
		typesort_sources = list(starmap(CBDBPerson, cursor.fetchall()))
		logging.info('%s corresponding %s with year(s) were retrieved from the database.' % (cursor.rowcount, typesort))
		if len(typesort_sources) > 0:
			typesort_profile, dynastynamelist, booknamelist, personcoutypesorter = profile_worker(typesort_sources, settings, f, prfltype=typesort)
			profile[typesort] = typesort_profile['count']
			profile[typesort + '_typelist'] = typesort_profile['typelist']
		else:
			profile[typesort] = 0

	#################################################
	# use time expressions
	#################################################

	if settings['UseTimeExpr']:
		logging.info('Checking for time expressions...')
		if isinstance(f, CAFrequencies):
			time_sources, timefreqs = time_detector(f.textrepr()) # if there's only 3-grams doesn't really make sense to check on time expressions, but we can still check for nianhao
		elif isinstance(f, TextFrequencies) and corpus:
			time_sources, timefreqs = time_detector(source.standardized, mode="full")
		else:
			time_sources, timefreqs = time_detector(sourcefile.standardized, mode="full")
		time_expressions = []
		if len(time_sources) > 0:
			logging.info('Loading data from DDBC time authority database...')
			for i, tm in enumerate(time_sources):
				cursor.execute(tm.sql())
				sqlresults = cursor.fetchall()
				# this is only for purpose of analyzing raw results
				# for row in sqlresults:
				# 	print(tm.expression + " – Result " + str(i) + ": " + str(row[0]) + "year " + str(row[1]) + " " + str(row[3]) + "–" + str(row[4]) + ", era: " + row[7] + ", emperor: " + row[8] + ", dynasty: " + row[9])
				try:
					startyear, endyear = sqlresults[0][3], sqlresults[-1][4]
				except:
					continue
				if endyear-startyear <= 50 and endyear >= startyear:
					tm.startyear, tm.endyear = startyear, endyear
					tm.emperor, tm.dynasty = sqlresults[0][8], sqlresults[0][9]
					tm.freq = timefreqs[tm.expression]
					logging.debug("🕰 startyear: " + str(startyear) +", endyear: " + str(endyear))
					time_expressions.append(tm)
		
		if len(time_expressions) > 0:
			time_expressions.sort(key=lambda t: t.endyear, reverse=True)
			timeprofile, dynastytimelist, booktimelist, timecounter = profile_worker(time_expressions, settings, prfltype='times')
			profile['times'] = timeprofile['count']
			profile['times_typelist'] = timeprofile['typelist']
		else:
			logging.info('Unable to detect any usable unambiguous time expressions in the text.')
			profile['times'] = 0
	else:
		profile['times'] = 0		

	#################################################
	# prepare and generate output
	#################################################

	profile['totals'] = profile['count']
	for typesort in typesorts:
		profile['totals'] += profile[typesort] # smoothed words + other vars
		
	logging.info("Processed " + str(counter['words']) + " words, " + str(counter['estimate']) + " based on estimations.")
	
	simplechronon, smoothedtargetline = profile_dater(profile, settings, profile_mode='smoothed')
	plainsimplechronon, plaintargetline = profile_dater(profile, settings, profile_mode='count')
	piotsimplechronon, piotrowskitargetline = profile_dater(profile, settings, profile_mode='piotrowskismoothed')
	if settings['UseCBDB']:
		simplechrononer, targetline = profile_dater(profile, settings, profile_mode='smoothed', ner=True)	
	if settings['UseTimeExpr']:
		newest_date_chronon = ndt_dater(profile)
		combochronon = max(newest_date_chronon, simplechrononer)

	ayl_header = '_' + str(settings['FreqListLength'])
	ayl, wayl, sayl, payl = counter['AverageSum'] / counter['words'], counter['WeightedAverageSum'] / counter['freqweighted'], counter['smoothedsum'] / counter['smoothedwords'], counter['piotsmoothedsum'] / counter['piotsmoothedwords']

	if corpus: # prepare output for a pre-dated text
		print("🐼 This is %s, %s (%s)." % (corpus.metadata.dc_title[sourcefile], sourcefile, corpus.metadata.cleanyear[sourcefile]))
		known_year, known_century = corpus.metadata.cleanyear[sourcefile], get_chronon_for_year(corpus.metadata.cleanyear[sourcefile], 100)
		simplechrondist, simplechrondmed = abs(known_century-simplechronon), abs(known_year-(simplechronon+50))
		simplechronhit = int(simplechronon) == int(known_century)
		piotsimplechrondist, piotsimplechrondmed = abs(known_century-piotsimplechronon), abs(known_year-(piotsimplechronon+50))
		piotsimplechronhit = int(piotsimplechronon) == int(known_century)
		plainsimplechrondist, plainsimplechrondmed = abs(known_century-plainsimplechronon), abs(known_year-(plainsimplechronon+50))
		plainsimplechronhit = int(plainsimplechronon) == int(known_century)
		
		smoothed_at_known = profile.loc[known_century].smoothed
		smoothed_at_previous = profile.loc[known_century-100].smoothed
		smoothed_at_next = profile.loc[known_century+100].smoothed if known_century < profile.index.max() else 0

		piotrowskismoothed_at_known = profile.loc[known_century].piotrowskismoothed
		piotrowskismoothed_at_previous = profile.loc[known_century-100].piotrowskismoothed
		piotrowskismoothed_at_next = profile.loc[known_century+100]['piotrowskismoothed'] if known_century < profile.index.max() else 0

		words_at_known = profile.loc[known_century]['count']
		words_at_previous = profile.loc[known_century-100]['count']
		words_at_next = profile.loc[known_century+100]['count'] if known_century < profile.index.max() else 0
		
		# ratio_max_at_known_century = profile.smoothed.max() / smoothed_at_known
		# ratio_first_at_known_century = profile.iloc[0].smoothed / smoothed_at_known
		# piotrowskiratio_max_at_known_century = profile.piotrowskismoothed.max() / piotrowskismoothed_at_known
		# piotrowskiratio_first_at_known_century = profile.iloc[0].piotrowskismoothed / piotrowskismoothed_at_known
		
		newer_partition = profile[profile.index > known_century]['count'].sum() / profile['count'].sum()
		newer_partition_smoothed = profile[profile.index > known_century]['smoothed'].sum() / profile['smoothed'].sum()
		newer_partition_piotsmoothed = profile[profile.index > known_century]['piotrowskismoothed'].sum() / profile['piotrowskismoothed'].sum()

		output_fieldnames = [
			'known_year', 'known_century', 'title', 'mingram', 'maxgram', 
			'gramstypes', 'gramstokens', 'gramshapaxes', 'totaltypes', 'total_at_known',
			'wordtypes', 'wordtokens', 'wordshapaxes', 'words_at_known', 'words_at_previous', 'words_at_next' ,'words_at_max', 'plaintargetline',
			'plainsimplechron', 'plainsimplechrondist', 'plainsimplechrondmed', 'plainsimplechronhit', 
			'smoothedtypes', 'smoothed_at_known', 'smoothed_at_previous', 'smoothed_at_next', 'smoothed_at_max', 'smoothedtargetline', 
			'simplechron', 'simplechrondist', 'simplechrondmed', 'simplechronhit', 		
			'piotrowskismoothedtypes', 'piotrowskismoothed_at_known', 'piotrowskismoothed_at_previous', 'piotrowskismoothed_at_next', 'piotrowskismoothed_at_max', 'piotrowskitargetline',
			'piotsimplechron', 'piotsimplechrondist', 'piotsimplechrondmed', 'piotsimplechronhit', 
			'newer_partition', 'newer_partition_smoothed', 'newer_partition_piotsmoothed', 
			'ayl' + ayl_header, 'wayl' + ayl_header, 'sayl' + ayl_header, 'payl' + ayl_header
			]
		output_content = [
			known_year, known_century, corpus.metadata.dc_title[sourcefile], settings['MinGram'], settings['MaxGram'], 
			f.gramstypecount, f.gramstokencount, f.gramshapaxes, profile.totals.sum(), profile.loc[known_century].totals,
			profile['count'].sum(), f.wordstokencount, f.wordshapaxes, words_at_known, words_at_previous, words_at_next, profile['count'].max(), plaintargetline,
			plainsimplechronon, plainsimplechrondist, plainsimplechrondmed, plainsimplechronhit, 
			profile.smoothed.sum(), smoothed_at_known, smoothed_at_previous, smoothed_at_next, profile.smoothed.max(), smoothedtargetline, 
			simplechronon, simplechrondist, simplechrondmed, simplechronhit,
			profile.piotrowskismoothed.sum(), piotrowskismoothed_at_known, piotrowskismoothed_at_previous, piotrowskismoothed_at_next, profile.piotrowskismoothed.max(), piotrowskitargetline,
			piotsimplechronon, piotsimplechrondist, piotsimplechrondmed, piotsimplechronhit,
			newer_partition, newer_partition_smoothed, newer_partition_piotsmoothed, 
			ayl, wayl, sayl, payl 			
			]

		if settings['UseCBDB']: # with name types available
			
			# ratio_max_at_known_century_ner = profile.totals.max() / total_at_known_century
			# ratio_first_at_known_century_ner = profile.iloc[0].totals / total_at_known_century
			simplechrononerdist, simplechrononerdmed = abs(known_century-simplechrononer), abs(known_year-(simplechrononer+50))
			simplechronerhit = int(simplechrononer) == int(known_century)

			names_at_known, places_at_known = profile.loc[known_century].names, profile.loc[known_century].places
			names_at_previous = profile.loc[known_century-100].names
			names_at_next = profile.loc[known_century+100].names if known_century < profile.index.max() else 0

			output_fieldnames.extend(['nametypes', 'nametokens', 'names_at_known', 'names_at_previous', 'names_at_next', 'names_at_max', 'simplechrononer', 'simplechronerhit', 'targetline'])
			output_content.extend([profile.names.sum(), f.nametokencount, names_at_known, names_at_previous, names_at_next, profile.names.max(), simplechrononer, simplechronerhit, targetline])

		if settings['UseCBDBPlaces']: # with place types available
			output_fieldnames.extend(['placetypes', 'placetokens'])
			output_content.extend([profile.places.sum(), f.placetokencount])

		if settings['UseTimeExpr']: # with time expressions available
			ndt_hit = int(newest_date_chronon) == int(known_century) if newest_date_chronon else False
			combochrondist, combochrondmed = abs(known_century-combochronon), abs(known_year-(combochronon+50))
			combochronhit = int(combochronon) == int(known_century)
			times_at_known = profile.loc[known_century].times
			times_at_next = profile.loc[known_century+100].times if known_century < profile.index.max() else 0

			output_fieldnames.extend(['timetypes', 'times_at_known', 'times_at_known', 'times_at_max', 'ndt_dated', 'ndt_hit', 'combochronon', 'combochrondist', 'combochrondmed', 'combochronhit'])
			output_content.extend([profile.times.sum(), times_at_known, times_at_next, profile.times.max(), newest_date_chronon, ndt_hit, combochronon, combochrondist, combochrondmed, combochronhit])

		observations = pd.DataFrame(columns=output_fieldnames) if observations == False else observations
		observations.loc[sourcefile] = output_content

	else: # observation file should be already there
		output_fieldnames = [
			'characters', 'mingram', 'maxgram', 
			'gramstypes', 'gramstokens', 'gramshapaxes', 'totaltypes',
			'wordtypes', 'wordtokens', 'wordshapaxes','words_at_max', 'plaintargetline', 'plainsimplechron', 
			'smoothedtypes', 'smoothed_at_max', 'smoothedtargetline', 'simplechron', 	
			'piotrowskismoothedtypes', 'piotrowskismoothed_at_max', 'piotrowskitargetline', 'piotsimplechron', 
			'ayl' + ayl_header, 'wayl' + ayl_header, 'sayl' + ayl_header, 'payl' + ayl_header
			]
		output_content = [
			len(sourcefile.text[current_part]), settings['MinGram'], settings['MaxGram'], 
			f.gramstypecount, f.gramstokencount, f.gramshapaxes, profile.totals.sum(), 
			profile['count'].sum(), f.wordstokencount, f.wordshapaxes, profile['count'].max(), plaintargetline, plainsimplechronon, 
			profile.smoothed.sum(), profile.smoothed.max(), smoothedtargetline, simplechronon, 
			profile.piotrowskismoothed.sum(), profile.piotrowskismoothed.max(), piotrowskitargetline, piotsimplechronon,
			ayl, wayl, sayl, payl 			
			]

		if settings['UseCBDB']:
			output_fieldnames.extend(['nametypes', 'nametokens', 'names_at_max', 'simplechrononer', 'targetline'])
			output_content.extend([profile.names.sum(), f.nametokencount, profile.names.max(), simplechrononer, targetline])

		if settings['UseCBDBPlaces']:
			output_fieldnames.extend(['placetypes', 'placetokens'])
			output_content.extend([profile.places.sum(), f.placetokencount])

		if settings['UseTimeExpr']:
			output_fieldnames.extend(['timetypes', 'times_at_max', 'ndt_dated', 'combochronon'])
			output_content.extend([profile.times.sum(), profile.times.max(), newest_date_chronon, combochronon])

		for fieldname, fieldcontent in zip(output_fieldnames, output_content):
			observations.at[(sourcefile.filename, current_part), fieldname] = fieldcontent

	#################################################
	# use statistical language models as well?
	#################################################

	if len(settings['ChrononMethods']) > 0:
		observationfile = 'results/chronon_observations_' + f.name + '_' + settings['ChrononModel'] + '_' + str(settings['MinGram']) + 'to' + str(settings['MaxGram']) + '_' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.xlsx'
		logging.info("🐍 Using %s from chronon path %s and storing in %s." % ('freq', settings['ChrononPath'], observationfile))
		chronon_observations = multichron(f, settings, corpus=False, known_year=False)
		chronon_observations.to_excel(observationfile, encoding='utf-8', index=True)
	
	for method in settings['ChrononMethods']:
		observations.at[(sourcefile.filename, current_part), method] = chronon_observations.iloc[0]['best'+method]

	#################################################
	# calculate AYL for given parameters
	#################################################
	
	for wfl in settings['WordFreqListLength']:
		try:
			observations.at[sourcefile.filename, 'ayl_w_' + str(wfl)] = counter['ayl_w_' + str(wfl)]
		except:
			logging.info("Cannot store AYL dating info.")

	if corpus:
		return(observations, profile)
	else:
		# logging.info("The text's average word creation year is calculated as " + str(int(observations.at[(sourcefile.filename, current_part), 'ayl' + ayl_header])) + ".")
		# logging.info("Taking word frequency into account, the text's average word creation year is calculated as " + str(int(observations.at[(sourcefile.filename, current_part), 'wayl' + ayl_header])) + ". This, too, is highly experimental.")
		# logging.info("Taking 漢語大詞典 bias into account, the text's average word creation year is calculated as " + str(int(observations.at[(sourcefile.filename, current_part), 'sayl' + ayl_header])) + ". This is even more experimental.")	
		return(dynastywordlist, bookwordlist, observations, profile)


#################################################
# provide neologism profiler functions
#################################################

def profile_worker(sources, settings, frequencies=False, prfltype='words'):
	"Type by type work of the textimator"
	logging.getLogger()
	logging.info(("The newest %s type found in the text is %s (recorded in 《%s》), %s–%s.") % (prfltype, sources[0].cleanword, sources[0].book, sources[0].startyear, sources[0].endyear))
	workprofile = century_profile_df(maxgrams=settings['MaxGram']) if prfltype == 'words' else century_profile_df(maxgrams=False)
	dyndict, dynastytypes, booktypes = defaultdict(int), defaultdict(list), defaultdict(list)
	counter = Counter()

	bar = ShadyBar('Working.', max=len(sources), width=60) if 'multiprocessing' not in sys.modules else False
	for t in sources:
		if frequencies:
			t.freq = frequencies.freq_dict[t.cleanword]
		try:
			dyndict[t.dynasty] += 1
		except:
			pass
		
		if isinstance(t, HYDCDWord) or isinstance(t, CBDBPerson):
			if t.estimate == '~': counter['estimate'] += 1
			counter['AverageSum'] += t.meanyear
			counter['WeightedAverageSum'] += (t.freq * t.meanyear)
		if isinstance(t, TimeMatch):
			counter['AverageSum'] += t.meanyear()
			counter['WeightedAverageSum'] += (t.freq * t.meanyear())
		counter['freqweighted'] += t.freq

		counter[prfltype] += 1
		type_len = t.length if prfltype == 'words' else False
		workprofile = slicemethod(workprofile, t.startyear, t.endyear, 'count', wordlength=type_len, centurytype=t.cleanword)

		if settings['NeologismByDynasty']: 
			dynastytypes[t.dynasty].append((t.cleanword, t.freq, t.book, t.estimate))
		if settings['NeologismByText']:
			booktypes[(t.book, t.startyear, t.endyear, t.dynasty)].append((t.cleanword, t.freq))

		if bar: bar.next()
	if bar: bar.finish()
	# todo, century, dynasty, book types not implememted yet
	# do multiple word AYL calculations
	if 'WordFreqListLength' in settings:
		if prfltype == 'words':
			# order the list of all types by their frequency
			sources.sort(key=lambda t: t.freq, reverse=True)
			for wfl in settings['WordFreqListLength']:
				if wfl <= 1:
					# do relative calc
					abslen = math.floor(wfl * len(sources))
				else:
					abslen = wfl
				if abslen <= len(sources):
					print("🐍 Calculating word based ayl for %s most frequent types." % (wfl))
					aylsum = sum(t.meanyear for t in sources[0:abslen-1])	
					counter['ayl_w_'+str(wfl)] = round(aylsum / abslen, 2)					
				else:
					print("🌊 Desired word list length %s exceeds type list length of %s." % (wfl, len(sources)))
	return(workprofile, dynastytypes, booktypes, counter)	


def profile_dater(prfl, settings, profile_mode='smoothed', ner=False, model='known_century'):
	"Guess publication century using neologism profile"
	safemin = 5
	namesafemin = 0.0085675 * prfl['names'].sum() + 3

	if profile_mode == 'count':
		if settings['MinGram'] == 2 and settings['UseDFZTraining'] == True:
			slope, intercept = 0.0019263, -2.5956728

	if profile_mode == 'smoothed':
		if settings['MinGram'] == 2 and settings['UseDFZTraining'] == True:	
			slope, intercept = 0.0031007, -6.5125941 # regressed to plain wordtypes

	if profile_mode == 'piotrowskismoothed':
		if settings['MinGram'] == 2 and settings['UseDFZTraining'] == True:	
			slope, intercept = 0.0013751, -3.2355946 # regressed to plain wordtypes

	if 'slope' not in locals():
		slope, intercept = 0.003, 4
		print("⚠️ Warning! Using fallback function, no trained model for current settings with %s–%s grams; use DFZ: %s, use Corpus: %s." % (settings['MinGram'], settings['MaxGram'], settings['UseDFZTraining'], settings['UseNonHYDCDEvidence']))

	target = prfl['count'].sum() * slope + intercept
	target = safemin if target < safemin else target # prevent negative target
	prfl = prfl.sort_index()

	prfl['distance_from_target'] = prfl.apply(lambda row: abs(row[profile_mode] - target), axis=1)
	century = prfl['distance_from_target'].idxmin() 
	# if model == 'previous_century' and century != 1900:
	# 	century += 100
	print("✏️  %s: Closest century to targetline is %s." % (profile_mode, century))

	# fallback method 1: next century has more lexicalization or previous has less? 
	try:
		if prfl.loc[century+100, profile_mode] > prfl.loc[century, profile_mode] or prfl.loc[century-100, profile_mode] < prfl.loc[century, profile_mode] or prfl.loc[century+200, profile_mode] > prfl.loc[century, profile_mode] or prfl.loc[century-200, profile_mode] < prfl.loc[century, profile_mode]:
			century = prfl[(prfl[profile_mode] >= target) & (prfl[profile_mode] >= safemin)].index.max()
			print("✏️  %s: Neighbour century correction, going to %s." % (profile_mode, century))
	except:
		pass

	if ner == True:
		# nametarget = prfl.names.sum() * nameslope + nameintercept
		# if prfl.names.sum() >= minnames:
			#namecenturies = prfl[(prfl.index > century) & (prfl.names >= nametarget) & (prfl.names >= namesafemin)].index
		namecenturies = prfl[(prfl.index > century) & (prfl.names > namesafemin) & (prfl[profile_mode] >= safemin)].index
		if len(namecenturies) > 0:
			#print("📔 %s total names projected to %s names at known." % (prfl.names.sum(), nametarget))
			print("🔍 Guessed newer century because of names: %s instead of %s." % (namecenturies.max(), century))
			century = namecenturies.max()
	
	# fallback method 2: steep to previous?
	try:
		while prfl.loc[century-100, profile_mode] > prfl.loc[century, profile_mode] * 4:
			century -= 100
			print("✏️  %s: Steep decrease, going to %s." % (profile_mode, century))
	except:
		pass


	return(century, target)

def ndt_dater(prfl):
	"Try to use newest time expression in text for dating purpose"
	threshold = 4
	century = prfl[(prfl.times >= threshold)].index.max()
	print("✏️  Newest century mentioned in text with at least %s year instances is %s." % (threshold, century))
	if math.isnan(century): 
		return(False)
	else:
		return(century)

def time_detector(text, mode="grams"):
	# timetagrex = "<nianhao>((<number>)|(<period>)|(<season>)|(<tgdz>)){2,}"
	timetagrex = "<nianhao>((<number>)年){1,}((<number>)|(<period>)|(<season>)|(<tgdz>)){1,}"
	if mode == 'grams':
		timetagrex = "<nianhao>((<number>)|(<period>)|(<season>)|(<tgdz>)){1,}"
		# timetagrex = "<nianhao>((<number>)){1,}"
	timerexp = grams_regex_builder(timetagrex) if mode == "grams" else regex_builder(timetagrex)
	timematches = re.finditer(timerexp, text)
	#timematches = re.finditer(timerexp, "同光二十年春癸未，皇帝御文明癸未殿.") # test string
	results, timefreqs = [], Counter()
	if timematches:
		for m in timematches:
			if m.group(0) not in timefreqs:
				tm = TimeMatch(m)
				results.append(tm)
			timefreqs[m.group(0)] += 1
	logging.info('Found %s time expression candidates in the text.' % (len(results)))
	return(results, timefreqs)

def slicemethod(profile, startyear, endyear, column='count', wordlength=False, centurytype=False):
	"distribute words over centuries if they can't be dated exactly"
	slicer, relevantcenturies = 0, sorted(century_dict(startyear, endyear))
	duration = endyear - startyear
	if len(relevantcenturies) == 1: # one century? go for it.
		profile.loc[relevantcenturies[0], column] += 1
		if centurytype: profile.loc[relevantcenturies[0], 'typelist'].append(centurytype)
		if wordlength: profile.loc[relevantcenturies[0], 'X' + str(wordlength)] += 1
	else:
		for century in relevantcenturies:
			if endyear >= (century + 100): # 
				currentslicedynyears = (century + 100) - (startyear + slicer) # wieviele aktien hat ein text im slice?
			else: # last century of the timespan:
				currentslicedynyears = endyear - (startyear + slicer)
			slicer += currentslicedynyears #
			profile.loc[century, column] += currentslicedynyears / float(duration) * 1.0
			if centurytype: profile.loc[century, 'typelist'].append(centurytype)
			if wordlength: profile.loc[century, 'X' + str(wordlength)] += currentslicedynyears / float(duration) * 1.0	
	return(profile)

def detailed_output(typelist, settings, text=False):
	if settings['ListOutput']:
		for t in typelist:
			print("\n%s,%s%s–%s,%s,%s," % (t.cleanword, t.estimate, t.startyear, t.endyear, t.book, t.freq))
			if settings['PrintConcordance']:
				try: 
					text.print_concordance(t.cleanword, width=settings['ConcordanceSentenceLength'], limit=settings['ConcordanceSize'])
				except:
					pass
	return True	