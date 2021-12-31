"""
Classify a bunch of [CrossAsia] n-gram data texts with a temporal language model.
Use even or Standard model. Exclude the data that was used in creation of the model.
Available methods:
* 'cossim' = Cosine similarity,
* 'tfidf' = Term frequency inverse document frequency weighted Cosine similarity,
* 'jacsim' = Jaccard similarity,
* 'kld' = Kullback Leibler Divergence 
* 'kld_te' = Temporal Entropy weighted KLD,
* 'nllr' = Normalized Log Likelihood Ratio,
* 'nllr_te' = Temporal Entropy weighted NLLR,
* 'rand' = Select a random chronon / used as baseline
"""

###########################################################
# import Python modules
###########################################################

import argparse, csv, gc, glob, json, math, multiprocessing, numpy as np, pandas as pd, random, sys
from collections import defaultdict, Counter, OrderedDict	
from datetime import datetime
from progress.bar import ShadyBar

###########################################################
# import own modules
###########################################################

from modules.classes3 import CAFrequencies, CAGrams, Dictionary, LanguageModel
from modules.settings3 import settingprinter, standardize_settings, compare_settings
from modules.initialize_logger3 import *
from modules.toolbox3 import term_frequency
from modules.similarities import Similarities

initialize_logger("corpusgrams_textchroncat3.log")

###########################################################
# settings, adjust to corpus properties
###########################################################

###########################################################
# CAUTION ALWAYS CHECK IF SETTINGS ARE CORRESPONDING TO CORPUS!
###########################################################

############################
# HDC corpus settings
############################

# settings = {'BaseChronon': -700, # adjust to model / or improve runtime performance by reducing chronon space
# 			'LastChronon': 1900,
# 			'Punctuation': False, # will load HYDCD Word list accordingly
#  			'MinGram': 1,  # will consider grams of minimum length n
#  			'MaxGram': 2, # will consider grams of maximum length n
#  			'LookupMinimumNgramCount': 1, # minimum absolute token frequency for consideration
#  			'FreqListLength': 1,
#  			'Exclude': False, # 'exclude_' # ''
#  			'Sample': 60, # 'results/chronon_observations_xx-skqs-gramschronons_allquotes_12_timewords_1to2_20210113-163331.csv', # 'results/chronon_observations_difangzhi-gramswords_1to2_20201205-114042.csv', # no 12, uses full word list # 100
#  			'Even': False, # True = use language model with equal amount of chronon dimensions 
#  			'ChrononDuration': 100, # model timespan of chronon
#  			'UseCBDB': False,
#  			'UseCBDBPlaces': False, 
#  			'UseTimeExpr': True,
#  			'HYDCDStandardize': False,
#  			'SmoothingMethod': False,
#  			'SmoothingParameter': 0.01, 
#  			'ChrononPath': 'models/chronons_allquotes_12_time/', # chrononpath = 'models/chronons_allquotes_14_time/'
#  			'ModelType': 'chronons'
#  			}

############################
# Difangzhi Chronon settings
############################

settings = {'BaseChronon': 1475,
			'LastChronon': 1875,
			'Punctuation': False, # will load HYDCD Word list accordingly
 			'MinGram': 1,  # will consider grams of minimum length n
 			'MaxGram': 2, # will consider grams of maximum length n
 			'LookupMinimumNgramCount': 1, # minimum absolute token frequency for consideration
 			'FreqListLength': 1,
 			'Exclude': True,
 			'Sample': 'results/sample_dfz216.csv', 
 			# 'Sample': 200, # how many texts 
 			'Even': False, # True = use language model with equal amount of chronon dimensions 
 			'ChrononDuration': 50, # model timespan of chronon
 			'UseCBDB': False,
 			'UseCBDBPlaces': False, 
 			'UseTimeExpr': True,
 			'HYDCDStandardize': False,
 			'SmoothingMethod': False,
 			'SmoothingParameter': 0.5,
			'ChrononPath': 'models/chronons_dfz_times_12_orig/',
			'ModelType': 'chronon'
 			} 	

############################
# XXSKQS Chronon settings
############################

# settings = {'BaseChronon': 1475, 
# 			'LastChronon': 1875,
# 			'Punctuation': True, # will load HYDCD Word list accordingly
#  			'MinGram': 1,  # will consider grams of minimum length n
#  			'MaxGram': 2, # will consider grams of maximum length n
#  			'LookupMinimumNgramCount': 1, # minimum absolute token frequency for consideration
#  			'FreqListLength': 1,
#  			'Exclude': True,
#  			'Sample': 'results/chronon_observations_xx-skqs-gramschronons_allquotes_12_timewords_1to2_20210120-121312.csv', # this is from HDC-corpus experiment
#  			# 'Sample': 'results/chronon_observations_xx-skqs-gramschronons_xxskqs_12_times_normwords_1to2_addyuanshan.csv', # use a new sample, but include Yuanshan!
#  			# 'Sample': 216, # make above sample, only 5 for 1675 and 2 for 1475
#  			'Even': False, # True = use language model with equal amount of chronon dimensions 
#  			'ChrononDuration': 50, # model timespan of chronon
#  			'UseCBDB': True,
#  			'UseCBDBPlaces': False, 
#  			'UseTimeExpr': True,
#  			'HYDCDStandardize': True,
#  			'SmoothingMethod': False,
#  			'SmoothingParameter': 0.5,
# 			'ChrononPath': 'models/chronons_xxskqs_12_times_norm/',
# 			'ModelType': 'chronon' # ModelType': 'document'
#  			} 	

############################
# XXSKQS Co-dating settings
############################

# settings = {'BaseChronon': 1475, 
# 			'LastChronon': 1875,
# 			'Punctuation': True, # will load HYDCD Word list accordingly
#  			'MinGram': 1,  # will consider grams of minimum length n
#  			'MaxGram': 2, # will consider grams of maximum length n
#  			'LookupMinimumNgramCount': 1, # minimum absolute token frequency for consideration
#  			'FreqListLength': 1,
#  			'Exclude': True,
#  			'Sample': 'results/chronon_observations_xx-skqs-gramschronons_xxskqs_12_times_normwords_1to2_addyuanshan.csv',
#  			'Even': False, # True = use language model with equal amount of chronon dimensions 
#  			'ChrononDuration': 50, # model timespan of chronon
#  			'UseCBDB': True,
#  			'UseCBDBPlaces': False, 
#  			'UseTimeExpr': True,
#  			'HYDCDStandardize': True,
#  			'SmoothingMethod': False,
#  			'SmoothingParameter': 0.5,
# 			'ChrononPath': 'models/codat_xxskqs_12_names_time_norm/',
# 			'ModelType': 'document' 
#  			} 			



settings = standardize_settings(settings)
settingprinter(settings)

methods = ['cossim', 'tfidf', 'jacsim', 'kld', 'kld_te', 'nllr', 'nllr_te', 'rand']

###########################################################
# check if settings are suitable 
###########################################################

try:
	with open(settings['ChrononPath'] + 'settings.json', 'r') as storage:
		model_settings = json.load(storage)
	check = compare_settings(settings, model_settings)
	logging.info(check)
except:
	logging.info("🐍 Model settings are not available. Proceeding without check.")

###########################################################
# get a path we want to analyze
###########################################################

# Check if there's something to exclude from the language model training data
if settings['Exclude']:
	metadatafiles, metadata = sorted(glob.glob(settings['ChrononPath'] + 'meta*.csv')), []
	if len(metadatafiles) > 0:
		logging.info("🐍 Checking corpus sources from training data for %s chronons." % (len(metadatafiles)))
	else:
		logging.warning("❌ No suitable data available in given corpus path %s. Aborting." % (settings['ChrononPath']))
		exit()
	for filename in metadatafiles:
		chronon_metadata = pd.read_csv(filename, index_col='dc_identifier') # get meta data
		metadata.append(chronon_metadata)
	metadata = pd.concat(metadata)
	metadata = metadata[~metadata.index.duplicated(keep='first')]
	corpus = CAGrams('difangzhi-grams', 'difangzhi-metadata.xlsx', settings['Sample'], exclude = metadata.index, minchronon = settings['BaseChronon'])
	# corpus = CAGrams('xx-skqs-grams', 'xuxiu_metadata_year.xlsx', settings['Sample'], exclude = metadata.index, minchronon = settings['BaseChronon'])
else:
	corpus = CAGrams('difangzhi-grams', 'difangzhi-metadata.xlsx', settings['Sample'], minchronon = settings['BaseChronon'])
	# corpus = CAGrams('xx-skqs-grams', 'xuxiu_metadata_year.xlsx', settings['Sample'])
	# corpus = CAGrams('zhengshi-grams', 'zhengshi-metadata.xlsx', settings['Sample'])
	logging.info("🐼 Got metadata for %s texts, sample: %s" % ((len(corpus.sample)), settings['Sample']))



###########################################################
# Grab command line arguments and load text
###########################################################

parser = argparse.ArgumentParser(description='Use [words] or n-[grams]?)')
parser.add_argument('mode', metavar='Mode', type=str, nargs='?', default='words', help='Consider all n-[grams] or [words] (standard)')
args = parser.parse_args()
modestring = 'words' if args.mode == 'words' else ''

###########################################################
# Initialize model and result file 
###########################################################

if args.mode == 'words':
	dict_entries = Dictionary(settings, full=True).alltypes()
	logging.info("📚 Maximum possible dimensions: %s." % len(dict_entries))
else:
	dict_entries = None

freqfileprefix = "even_freq" if settings['Even'] else "freq"

model = LanguageModel(settings['ChrononPath'], freqfileprefix, args.mode, smoothing=settings['SmoothingParameter'], modeltype=settings['ModelType'])

logging.info("🐍 Using %.8f for longest chronon minimum smoothing." % (model.longchronminfreq))

observationfile = 'results/chronon_observations_' + corpus.name + model.name + args.mode + '_' + str(settings['MinGram']) + 'to' + str(settings['MaxGram']) + '_' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.csv'
logging.info("🐍 Using %s from chronon path %s and storing in %s." % (freqfileprefix, settings['ChrononPath'], observationfile))

###########################################################
# Do similarity checks
###########################################################

def multichron(source):
	"Process a text and do multiple similarity checks"
	i, sourcefile = source
	# initialize the result file
	# observations = pd.DataFrame(data={'filename': [corpus.sample.index[0]], 'chronon': [0], 'obstype': ['start'], 'title': [corpus.sample.dc_title[corpus.sample.index[i]]], 'hydcd_name': [''], 'observation': [i], 'year': [corpus.sample.cleanyear[corpus.sample.index[i]]]})
	observations = pd.DataFrame(data={'filename': [], 'chronon': [], 'obstype': [], 'title': [], 'hydcd_name': [], 'observation': [], 'year': []})
	observations = observations.set_index(['filename', 'chronon', 'obstype'])

	logging.info("📕 %s (%s) is analyzed." % (corpus.sample.dc_title[sourcefile], corpus.sample.cleanyear[sourcefile]))
	frequencies = CAFrequencies(corpus.name, sourcefile + '.txt', settings, dictionary=dict_entries, relative=True)
	
	dimensions, dimensions_tfidf = dict(), dict()
	
	for chronon in model.chronons:	
		print("📕 Matching chronon %s for %s (in task %s of %s).                                       " % (chronon, corpus.sample.dc_title[sourcefile], i+1, len(corpus.sample)), end="\r")

		if not (sourcefile, chronon, 'start') in observations.index:
			###########################################################
			# perform insert on dataframe for next part if necessary
			###########################################################
			row_to_append = pd.Series([corpus.sample.dc_title[sourcefile], i, corpus.sample.cleanyear[sourcefile]])
			observations.loc[(sourcefile, chronon, 'start'),['title', 'observation', 'year']] = row_to_append.values
			row_to_append = pd.Series([i, corpus.sample.cleanyear[sourcefile]])
			observations.loc[(sourcefile, chronon, 'end'),['observation', 'year']] = row_to_append.values

		usable = set(model.chrondict[chronon].keys()) & set(getattr(frequencies, modestring + 'relfreq_dict').keys())
		dimensions[chronon] = str(len(usable))
		observations.loc[(sourcefile, chronon, 'start'), 'dimensions'] = dimensions[chronon]
		
		sims = Similarities(getattr(frequencies, modestring + 'relfreq_dict'), model.chrondict[chronon], corpfreq=model.corpusdict, entropy_dict=model.tedict, tfidf_dict=model.chrondict_tfidf[chronon], totaltokens=getattr(frequencies, modestring + 'tokencount'), dummyfreq=model.longchronminfreq, idf_dict=model.chrondict_idf[chronon], model_type=settings['ModelType'])

		for method in methods:
			observations.loc[(sourcefile, chronon, 'start'), method] = getattr(sims, method)()

	###########################################################
	# Store results
	###########################################################
	known_year = corpus.sample.cleanyear[sourcefile]

	for method in methods:
		if 'kld' in method:
			maxchron = observations.xs([sourcefile, 'start'], level=['filename','obstype'])[method].idxmin()
		elif method == 'rand':
			maxchron = random.choice(list(dimensions.keys()))
		else:
			maxchron = observations.xs([sourcefile, 'start'], level=['filename','obstype'])[method].idxmax()
		
		try: # need to check if maxchron is actually a chronon
			maxchron = float(maxchron)
		except: # or a certain document we need to get the chronon for
			maxchron = (settings['ChrononDuration']/2) * math.floor(metadata.startyear[maxchron]/(settings['ChrononDuration']/2))

		distance_start, distance_end = maxchron - known_year, maxchron + settings['ChrononDuration'] - known_year
		distance_med = float(abs(distance_end) + abs(distance_start)) / 2

		chronhit = maxchron <= known_year <= maxchron + settings['ChrononDuration']
		observations.loc[(sourcefile, settings['BaseChronon'], 'start'), 'best' + method] = maxchron
		observations.loc[(sourcefile, settings['BaseChronon'], 'end'), 'best' + method] = maxchron + settings['ChrononDuration']
		observations.loc[(sourcefile, settings['BaseChronon'], 'start'), method + 'dist'] = distance_start
		observations.loc[(sourcefile, settings['BaseChronon'], 'end'), method + 'dist'] = distance_end
		observations.loc[(sourcefile, settings['BaseChronon'], 'start'), method + 'dmed'] = distance_med
		observations.loc[(sourcefile, settings['BaseChronon'], 'end'), method + 'dmed'] = distance_med
		observations.loc[(sourcefile, settings['BaseChronon'], 'start'), method + 'hit'] = str(chronhit).upper()
		observations.loc[(sourcefile, settings['BaseChronon'], 'end'), method + 'hit'] = str(chronhit).upper()
		print('🐍 Closest chronon for %s using %s was %s–%s. (%s years from %s) ' % (observations.loc[(sourcefile, settings['BaseChronon'], 'start'), 'title'], method, maxchron, maxchron+settings['ChrononDuration'], distance_med, known_year), end="\r")

	gc.collect()
	return observations

###########################################################
# Pseudo-Main
###########################################################

multiprocessing.set_start_method('fork')
if settings['ModelType'] == 'chronon':
	pool = multiprocessing.Pool(multiprocessing.cpu_count()-3)
else:
	pool = multiprocessing.Pool(6)
results = pool.map(multichron, enumerate(corpus.sample.index))
pool.close()

# results = []
# for i, text in enumerate(corpus.sample.index):
# 	obs = multichron((i, text))
# 	results.append(obs)

observations = pd.concat(results)
observations.to_csv(observationfile, encoding='utf-8', index=True)
logging.info("🐼 Results saved to %s" % (observationfile))

logging.info("🐍 Total %s model length is %s." % (model.name, model.size))
logging.info("Method: \t Precision (%) \t Error (years)") 
for method in methods:
	logging.info("%s:\t\t %.1f \t %.2f years." % (method, observations.xs([settings['BaseChronon'], 'start'], level=['chronon', 'obstype'])[method + 'hit'].map({'FALSE':False ,'TRUE':True}).sum() / len(corpus.sample) * 100, observations.xs([settings['BaseChronon'], 'start'], level=['chronon', 'obstype'])[method + 'dmed'].mean()))
 
print("\a\a\n")
