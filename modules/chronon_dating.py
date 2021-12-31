###########################################################
# Run chronon similarity on input text or grams
# based on multi_corpusgrams_textchroncat3 experiments
###########################################################

###########################################################
# Import Python modules
###########################################################

import glob, csv, logging, numpy as np, pandas as pd, random, sys
from collections import defaultdict, Counter, OrderedDict
from datetime import datetime
from progress.bar import ShadyBar

###########################################################
# Import own modules
###########################################################

from modules.similarities import cossim, jacsim, nllr, kld

class ChrononModel():
	"This is the descriptive container of the temporal language model"
	def __init__(self, chrononpath, methods, freqfileprefix='even_freq', mode='words'):
		chrononpath = 'models/' + chrononpath + '/'
		filenames = sorted(glob.glob(chrononpath + freqfileprefix + mode+"_*.csv"))
		self.chronons, self.cfreqfiles = [], dict()
		for csvfile in filenames:
			chronon = int(csvfile.replace(chrononpath + freqfileprefix + mode + "_", '').replace('.csv',''))			
			self.chronons.append(chronon)
			self.cfreqfiles[chronon] = csvfile
		self.chronons = sorted(self.chronons)
		self.chronon_count = len(self.chronons)
		self.first_chronon = self.chronons[0]

		self.overlap = np.diff(self.chronons)[-1]
		self.chronon_duration = np.diff(self.chronons[::2])[-1]

		if any('nllr' in m for m in methods):
			print("🐼 Loading corpus frequencies...")
			corpus_frequencies = pd.read_csv(chrononpath + mode + "totals.csv", index_col='item')
			self.corpusdict = corpus_frequencies['freq'].to_dict()

		if any('te' in m for m in methods):
			print("🐼 Loading temporal entropy...")
			self.tedict = corpus_frequencies['terel'].to_dict()

	def __len__(self):
		return self.chronon_count

	def chrondict(self, chronon):
		chrondict_loader = pd.read_csv(self.cfreqfiles[chronon], index_col='item') 
		chrondict = chrondict_loader['freq'].to_dict()
		return chrondict		

def multichron(f, settings, mode='words', methods=['nllr-te', 'kld-te'], corpus=False, known_year=False):
	chrononpath = settings['ChrononPath']
	mode, methods = settings['ChrononModel'], settings['ChrononMethods']
	modestring = 'words' if mode == 'words' else ''
	# freqfileprefix = "even_freq" # TODO, is this really better, or what?

	###########################################################
	# Initialize the detail results
	###########################################################

	observations = pd.DataFrame(data={'filename': [], 'chronon': [], 'obstype': [], 'title': [], 'hydcd_name': [], 'observation': [], 'year': []})
	observations = observations.set_index(['filename', 'chronon', 'obstype'])

	chronon_model = ChrononModel(chrononpath, methods, mode=mode)

	for i, chronon in enumerate(chronon_model.chronons):	
		print("📕 Matching chronon %s for %s (task %s of %s). " % (chronon, f.name, i+1, chronon_model.chronon_count), end="\r")
		
		if not (f.name, chronon, 'start') in observations.index:
			###########################################################
			# perform insert on dataframe for next part if necessary
			###########################################################
			# row_to_append = pd.Series([corpus.sample.dc_title[sourcefile], i, corpus.sample.cleanyear[sourcefile]])
			row_to_append = pd.Series([f.name, i, known_year])
			observations.loc[(f.name, chronon, 'start'),['title', 'observation', 'year']] = row_to_append.values
			# row_to_append = pd.Series([i, corpus.sample.cleanyear[sourcefile]])
			row_to_append = pd.Series([i, known_year])
			observations.loc[(f.name, chronon, 'end'),['observation', 'year']] = row_to_append.values

		chrondict = chronon_model.chrondict(chronon)
		# use only dimensions where we have data
		usable = set(chrondict.keys()) & set(getattr(f, modestring + 'relfreq_dict').keys())
		observations.loc[(f.name, chronon, 'start'), 'dimensions'] = len(usable)

		if 'jac' in methods:
			observations.loc[(f.name, chronon, 'start'), 'jacsim'] = jacsim(chrondict, getattr(f, modestring + 'relfreq_dict'))

		if 'kld' in methods:
			observations.loc[(f.name, chronon, 'start'), 'kld'] = kld(getattr(f, modestring + 'relfreq_dict'), chrondict)

		if 'kld-te' in methods:
			observations.loc[(f.name, chronon, 'start'), 'kld-te'] = kld(getattr(f, modestring + 'relfreq_dict'), chrondict, chronon_model.tedict)

		if 'nllr' in methods:
			observations.loc[(f.name, chronon, 'start'), 'nllr'] = nllr(getattr(f, modestring + 'relfreq_dict'), chrondict, chronon_model.corpusdict)

		if 'nllr-te' in methods:
			observations.loc[(f.name, chronon, 'start'), 'nllr-te'] = nllr(getattr(f, modestring + 'relfreq_dict'), chrondict, chronon_model.corpusdict, chronon_model.tedict)

	###########################################################
	# Get best chronons and store results
	###########################################################

	for method in methods:
		if method == 'kld' or method == 'kld-te':
			maxchron = observations[method].idxmin()[1]
			# maxchron = min([(sim, chron) for chron, sim in chrononsims[method].items()])[1]
		elif method == 'rand':
			maxchron = random.choice(chronon_model.chronons)
		else:
			maxchron = observations[method].idxmax()[1]
		observations.loc[(f.name, chronon_model.first_chronon, 'start'), 'best' + method] = maxchron
		observations.loc[(f.name, chronon_model.first_chronon, 'end'), 'best' + method] = maxchron + chronon_model.chronon_duration
		if known_year:
			distance_start, distance_end = maxchron - known_year, maxchron + chronon_model.chronon_duration - known_year
			distance_med = float(abs(distance_end) + abs(distance_start)) / 2
			chronhit = maxchron <= known_year <= maxchron + chronon_model.chronon_duration
			observations.loc[(f.name, chronon_model.first_chronon, 'start'), method + 'dist'] = distance_start
			observations.loc[(f.name, chronon_model.first_chronon, 'end'), method + 'dist'] = distance_end
			observations.loc[(f.name, chronon_model.first_chronon, 'start'), method + 'dmed'] = distance_med
			observations.loc[(f.name, chronon_model.first_chronon, 'end'), method + 'dmed'] = distance_med
			observations.loc[(f.name, chronon_model.first_chronon, 'start'), method + 'hit'] = str(chronhit).upper()
			observations.loc[(f.name, chronon_model.first_chronon, 'end'), method + 'hit'] = str(chronhit).upper()
			logging.info('🐍 Closest chronon for %s using %s was %s–%s. (%s years from %s) ' % (observations.loc[(f.name, chronon_model.first_chronon, 'start'), 'title'], method, maxchron, maxchron+chronon_model.chronon_duration, distance_start, known_year))
		else:
			logging.info('🐍 Closest chronon for %s using %s was %s–%s.  ' % (observations.loc[(f.name, chronon_model.first_chronon, 'start'), 'title'], method, maxchron, maxchron+chronon_model.chronon_duration))
			
	return observations
