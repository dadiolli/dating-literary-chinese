import codecs, glob, logging, mafan, math, pandas as pd, pycnnum, operator, os, regex as re, textwrap
from numpy import loadtxt
from collections import Counter
from pathlib import PurePath
from progress.bar import ShadyBar
from modules.dynasties3 import dynasty_handler, dynasty_handler_fanti
from modules.toolbox3 import find_ngrams, simplifieddetector, term_frequency
from modules.cleanhan3 import hydcd_standardize, hanwithpunctuation, hanonly
from nltk import FreqDist
from bs4 import BeautifulSoup

punctuation = re.compile(r"[,;?!？！；：，、“”‘’『』「」。]")
ik_punctuation = re.compile(r"[,;?!？！；：，、‘’“”]")

class Dictionary():
	"""Load a list of types to be used. 
	   Full uses words without temporal information, 
	   e. g. for temporal corpus models."""
	def __init__(self, settings, full=False):
		full = '_full_' if full else '_'
		dict_words = open('hydcd/wordlist' + full + 'punctuation_' + str(settings['Punctuation']).lower() + '.txt', 'r') # get word list from file (faster than db)
		self.words = self.reduce_grams(set(dict_words.read().split('\n')), settings['MinGram'], settings['MaxGram'])

		if settings['UseCBDB']:
			cbdb_names = open('hydcd/cbdb_unique_names.txt', 'r') # get word list from file (faster than db)
			self.cbdb_names = set(cbdb_names.read().split('\n'))
		else:
			self.cbdb_names = set()
		
		if settings['UseCBDBPlaces']:
			cbdb_places = open('hydcd/cbdb_unique_places.txt', 'r') # get word list from file (faster than db)
			self.cbdb_places = set(cbdb_places.read().split('\n'))
		else:
			self.cbdb_places = set()

		if settings['UseTimeExpr']:
			time_expr = open('hydcd/time_expressions.txt', 'r') # get word list from file (faster than db)
			self.time_expr = set(time_expr.read().split('\n'))
		else:
			self.time_expr = set()

	def alltypes_as_index(self):
		return pd.Index(self.words | self.cbdb_names | self.cbdb_places | self.time_expr)

	def alltypes(self):
		return self.words | self.cbdb_names | self.cbdb_places | self.time_expr

	def reduce_grams(self, input, mingramlength, maxgramlength):
		return set([x for x in input if len(x) >= mingramlength and len(x) <= maxgramlength])


class PlainTextCorpus():
	def __init__(self, name, path):
		self.name = name
		self.path = path
		try:
			self.metadata = pd.read_excel(path + '/' + 'metadata.xlsx', index_col = 0)
			self.sample = self.metadata
		except:
			print("❎ Can't load metadata for %s." % (self.name))
			exit()
		# check if all the listed files are available, so we can work with the data
		for filename, row in self.metadata.iterrows():
			if not os.path.isfile(path + '/' + filename):
				print("❎ File does not exist: %s." % (filename))

class CAGrams():
	"Create a CrossAsia n-grams object"
	def __init__(self, name, metafile, samplesize=0, minchronon=None, exclude=False):
		
		try:
			samplesize = int(samplesize)
			sampledata = None
		except:
			try:
				logging.info("✅ Loading sample data from %s..." % (samplesize))
				sampledata, samplesize = pd.read_csv(samplesize, index_col='filename'), False
			except:
				try: 
					sampledata, samplesize = pd.read_excel(samplesize, index_col='source'), False
				except:
					print("❎ Can't load sample data from %s." % (samplesize))
					exit()

		self.name = name
		self.metadata = pd.read_excel('primary_sources/' + name + '/' + metafile, index_col = 0)
		# fix for "broken" CrossAsia ngram counts
		gs = Giftschrank(name)
		self.metadata = self.metadata.drop(gs.schrank)

		# but that is not enough, some index ids have duplicates, such as fbfd08097f0af325b0bf72b64df1a2bb!
		# so it is actually unclear where they belong :/
		self.metadata = self.metadata[~self.metadata.index.duplicated(keep=False)] # drops 10 rows
		
		if self.name == 'xx-skqs-grams':
			# only lines with zhuan 撰 "authored by" 
			self.metadata = self.metadata[self.metadata['mods_responsibility'].str.contains('撰$', regex=True)]
			# self.metadata = self.metadata[~self.metadata['dc_title'].str.contains('[考譯集補注譜解]', regex=True)] # exclude texts including earlier texts

			self.metadata['authordyn'] = self.metadata.apply(lambda row: self.extract_dynasty(row['mods_responsibility']), axis=1)
			# author and published dynasty should be alike, otherwise we don't make sense here.
			self.metadata = self.metadata.loc[self.metadata['authordyn'] == self.metadata['dcterms_temporal']]
		
		if self.name == 'difangzhi-grams':
			# drop rows with missing or incomplete temporal data
			self.metadata = self.metadata.dropna(subset=['dc_creator']).dropna(subset=['dcterms_temporal.1']).dropna(subset=['dcterms_issued'])
			self.metadata['authordyn'] = self.metadata.apply(lambda row: self.extract_dynasty(row['dc_creator']), axis=1)
			# drop row if we can't get author's dynasty
			self.metadata = self.metadata.dropna(subset=['authordyn'])			
			self.metadata['cleanyear_era'] = self.metadata.apply(lambda row: self.cleanyear(row['dcterms_temporal.1'])[0], axis=1)
			# drop rows with missing or incomplete temporal data
			self.metadata = self.metadata.dropna(subset=['cleanyear_era'])
			self.metadata['startyear_era'] = self.metadata.apply(lambda row: self.cleanyear(row['dcterms_temporal.1'])[1], axis=1)
			self.metadata['endyear_era'] = self.metadata.apply(lambda row: self.cleanyear(row['dcterms_temporal.1'])[2], axis=1)

		if self.name != 'zhengshi-grams':
			self.metadata['cleanyear'] = self.metadata.apply(lambda row: self.cleanyear(row['dcterms_issued'])[0], axis=1)
			# drop rows with missing or incomplete temporal data
			
			self.metadata = self.metadata.dropna(subset=['cleanyear'])
			self.metadata['startyear'] = self.metadata.apply(lambda row: self.cleanyear(row['dcterms_issued'])[1], axis=1)
			self.metadata['endyear'] = self.metadata.apply(lambda row: self.cleanyear(row['dcterms_issued'])[2], axis=1)
			self.metadata['interval'] = self.metadata['endyear'] - self.metadata['startyear']
			self.metadata['dynasty'] = self.metadata.apply(lambda row: dynasty_handler_fanti(int(row['cleanyear'])).name, axis=1)
			self.metadata = self.metadata.dropna(subset=['cleanyear'])
			if minchronon:
				self.metadata = self.metadata.loc[(self.metadata['startyear'] >= minchronon)]

		if self.name == 'difangzhi-grams':
			# check if dynasty from dc_creator matches dynasty of dcterms_issued, ca. 7839 texts here 
			self.metadata = self.metadata.loc[(self.metadata['authordyn'] == self.metadata['dynasty'])] # reduce to ca. 7027
			# check if startyear from dcterms_issued is not more than 50 years later than dcterms_tenporal
			self.metadata = self.metadata.loc[(self.metadata['startyear'] <= self.metadata['endyear_era'] + 50)] # reduce to ca. 6879

		if isinstance(exclude, pd.Index):
			self.metadata = self.metadata.drop(exclude)
		
		if sampledata is not None:
			self.sample = self.metadata[self.metadata.index.isin(sampledata.index)]

		if self.name == 'zhengshi-grams':
			self.sample = self.metadata
		elif self.name in ['difangzhi-grams', 'xx-skqs-grams'] and sampledata is None:
			startyear, endyear, chrononduration = 1475, 1925, 50
			# startyear, endyear, chrononduration = 1300, 2000, 100
			sample, chrononcount = [], len(range(startyear,endyear,chrononduration)) # 12
			subsamplesize = round(samplesize/chrononcount)
			for c in range(startyear, endyear, chrononduration): # do not overlap here, or duplicates may be found
				print(c, chrononduration, subsamplesize)
				try: 
					sample.append(self.metadata.loc[(self.metadata['cleanyear'] >= c) & (self.metadata['cleanyear'] <= c+chrononduration)].sample(subsamplesize))
				except:
					logging.info("Not enough data, reducing subsample size for chronon %s to %s." % (c, len(self.metadata.loc[(self.metadata['cleanyear'] >= c) & (self.metadata['cleanyear'] <= c+chrononduration)])))
					sample.append(self.metadata.loc[(self.metadata['cleanyear'] >= c) & (self.metadata['cleanyear'] <= c+chrononduration)])
			self.sample = pd.concat(sample)
		else: # use given int as sample size to collect new random sample
			if sampledata is None: self.sample = self.metadata.sample(n=samplesize)

	def cleanyear(self, tempstring):
		if '-' in str(tempstring):
			try:
				startyear, endyear = tempstring.split('-')
				cleanyear = (int(startyear) + int(endyear)) / 2
				return(cleanyear, int(startyear), int(endyear))
			except:
				return(None, None, None)
		else:
			try:
				cleanyear = int(tempstring)
				if -1100 <= cleanyear <= 2019: # check if year is meaningful
					return(cleanyear, cleanyear, cleanyear)
				else:
					return(None, None, None)
			except:
				return(None, None, None)

	def extract_dynasty(self, dynastyauthor):
		if self.name == 'difangzhi-grams':
			pattern = re.compile(r'（([\w]+)）', re.UNICODE)
		elif self.name == 'xx-skqs-grams':
			pattern = re.compile(r'\[([\w]+)\]', re.UNICODE)
		else:
			print("Don't know how to do this.")
			return(None)
		try:
			dynasty = re.search(pattern, dynastyauthor).group(1)
		except:
			dynasty = None
		return(dynasty)

class CAFrequencies():
	"""Data container for text frequency data from CrossAsia n-gram service
	   use with dictionary as set to limit dimensions. Use names, places seperately if needed seperately.
	   Set relative to True to get relative counts based on total token amount."""
	def __init__(self, path, filename, settings = {}, dictionary=None, relative=False, names=False, places=False):
		assert settings, "❎ I need settings for MinGram and MaxGram."	
		###########################################################
		# get the frequency data from files
		###########################################################
		inputdata, self.alltypes, self.data_ok = list(), {}, True
		for n in range(settings['MinGram'], settings['MaxGram']+1):
			# assure data quality 
			tempgrams = pd.read_csv('primary_sources/' + path + '/' + str(n) + 'gram' + '/' + filename, sep="\t", header=None, names=['tokens'])
			if len(tempgrams.index[0]) == n:
				inputdata.append(pd.read_csv('primary_sources/' + path + '/' + str(n) + 'gram' + '/' + filename, sep="\t", header=None, names=['tokens']))
			else:
				print("❎ There's a problem with CrossAsia %s-Gram data for %s." % (n, filename))
				self.data_ok = False
				inputdata.append(pd.read_csv('primary_sources/' + path + '/' + str(n) + 'gram' + '/' + filename, sep="\t", header=None, names=['tokens']))
							
		self.freq_frame = pd.concat(inputdata)

		if 'LookupMinimumNgramCount' in settings and settings['LookupMinimumNgramCount'] > 1:
			self.freq_frame = self.freq_frame.loc[self.freq_frame.tokens >= settings['LookupMinimumNgramCount']]

		if 'SmoothingMethod' in settings and settings['SmoothingMethod'] == 'plusone':
			self.freq_frame['tokens'] = self.freq_frame['tokens'].astype(float)
			self.freq_frame['tokens'] += 0.5

		# experiment: use all the unigram types 
		if 'AllUnigrams' in settings and settings['AllUnigrams'] == True: 
			unigram_types = set([x for x in self.freq_frame.index if len(x) == 1])
			print("Found %s unigram types" % len(unigram_types))

		if 'HYDCDStandardize' in settings and settings['HYDCDStandardize'] == True:
			self.freq_frame['charlength'] = self.freq_frame.apply(lambda row: len(row.name), axis=1)
			# don't standardize chars, only bigrams, trigrams... chars won't help to find new dimensions
			# self.freq_frame.index = self.freq_frame.apply(lambda row: hydcd_standardize(row.name) if row.charlength > 1 else row.name, axis=1)
			self.freq_frame.index = self.freq_frame.apply(lambda row: hydcd_standardize(row.name), axis=1)
			self.freq_frame = self.freq_frame.groupby(level=0).sum()

		self.gramstypes = self.alltypes['grams'] = set(self.freq_frame.index)
		self.gramstypecount = len(self.gramstypes)
		self.gramstokencount = self.tokencount = self.freq_frame.tokens.sum()
		self.gramstokenmax = self.freq_frame.tokens.max()
		self.name = filename

		if relative:
			# self.relfreq_dict = {gram: float(self.freq_dict[gram]) / self.gramstokencount for gram in self.gramstypes}
			self.freq_frame['freq'] = self.freq_frame.apply(lambda row: term_frequency(row.tokens, self.gramstokencount, self.gramstokenmax, self.gramstypecount), axis=1)
			self.relfreq_dict = self.freq_frame['freq'].to_dict()
		self.freq_dict = self.freq_frame['tokens'].to_dict()	
		self.gramshapaxes = sum(map((1).__eq__, self.freq_dict.values())) / len(self.freq_dict)
		# logging.info("📕 The data contains " + str(len(self.gramstypes)) + " different " + str(settings['MinGram']) + "-" + str(settings['MaxGram']) +"-grams.")

		if dictionary:
			self.wordtypes = self.alltypes['words'] = self.gramstypes & dictionary
			self.wordstypecount = len(self.wordtypes)
			
			if 'AllUnigrams' in settings and settings['AllUnigrams'] == True: 
				print("Have %s word types without/before adding additional unigrams." % (len(self.wordtypes)))				
				if 'HYDCDStandardize' in settings and settings['HYDCDStandardize'] == True:
					from modules.cleanhan3 import unicode_variants
					replaced_chars = set(unicode_variants.keys())
					unigram_types = unigram_types - replaced_chars # don't re-add what we normalized away
					
				self.wordtypes = self.wordtypes.union(unigram_types)

				self.wordstypecount = len(self.wordtypes)
				print("Have %s word types after adding additional unigrams." % (self.wordstypecount))
	
			if len(self.wordtypes) > 0:
				
				self.wordsfreq_dict = {word: self.freq_dict[word] for word in self.wordtypes}
				self.wordshapaxes = sum(map((1).__eq__, self.wordsfreq_dict.values())) / len(self.wordsfreq_dict)
				self.wordstokencount = sum(self.wordsfreq_dict.values())
				self.wordstokenmax = max(self.wordsfreq_dict.values())
				# print("Total token sum before recount in %s is %s." % (self.name, self.wordstokencount))				
				if relative:
					self.wordsrelfreq_dict = dict((w, term_frequency(f, self.wordstokencount, self.wordstokenmax, self.wordstypecount)) for w, f in self.wordsfreq_dict.items())
			else:
				logging.info("❎ No word dimensions to work with.")
				print(filename)
				self.wordsfreq_dict, self.wordsrelfreq_dict, self.wordstokencount = {}, {}, 0
			# assert len(self.wordtypes) > 0, "❎ No word dimensions to work with."
		else: 
			self.wordtypes = {}
			
			# logging.info("📕 The text contains %s word types with a total of %s word tokens." % (len(self.wordtypes), self.wordstokencount))	
		# self.freq_grams = set([x[0] for x in self.ngram_freqlist if x[1] >= settings['LookupMinimumNgramCount']])
		# self.freqlistlength = len(self.freq_grams)		
		if names:
			self.nametypes = self.alltypes['names'] = self.gramstypes & names
			self.nametypecount = len(self.nametypes)
			if len(self.nametypes) > 0:
				self.namefreq_dict = {name: self.freq_dict[name] for name in self.nametypes}
				self.nametokencount = sum(self.namefreq_dict.values())
			else:
				logging.info("❎ No person names work to with.")
				self.namefreq_dict, self.nametokencount = {}, 0
				self.nametokencount = 0
			if relative:
				self.namerelfreq_dict = dict((p, float(f) / self.nametokencount) for p, f in self.namefreq_dict.items())
			logging.info("📕 The text contains %s name types with a total of %s possible person name tokens." % (len(self.nametypes), self.nametokencount))
		else:
			self.nametypes = {}

		if places:
			self.placetypes = self.alltypes['places'] = self.gramstypes & places
			self.placetypecount = len(self.placetypes)
			if len(self.placetypes) > 0:
				self.placefreq_dict = {name: self.freq_dict[name] for name in self.placetypes}
				self.placetokencount = sum(self.placefreq_dict.values())
			else:
				logging.info("❎ No place names work to with.")
				self.placefreq_dict, self.placetokencount = {}, 0
				self.placetokencount = 0
			if relative:
				self.placerelfreq_dict = dict((p, float(f) / self.placetokencount) for p, f in self.placefreq_dict.items())
			logging.info("📕 The text contains %s place name types with a total of %s possible place name tokens." % (len(self.placetypes), self.placetokencount))
		else:
			self.placetypes = {}

	def textrepr(self):
		return("。".join(self.gramstypes))


class HYDCDBook():
	def __init__(self, bid, title, author, startyear, endyear, dynasty):
		self.id = bid
		self.title = title
		self.jianti = mafan.simplify(self.title)
		self.author = author
		if self.author:
			self.author_jianti = mafan.simplify(author)
		self.startyear = startyear
		self.endyear = endyear
		self.dynasty = dynasty

class HYDCDWord():
	def __init__(self, wid, cleanword, book, startyear, endyear, usecount, estimate, dynasty):
		self.id = wid
		self.cleanword = cleanword
		self.length = len(cleanword)
		self.book = book
		self.startyear = startyear
		self.endyear = endyear
		self.usecount = usecount
		self.precision = estimate
		if self.startyear == self.endyear: # we know the exact year
			self.estimate = ''
			self.duration = 1
		else: 
			self.estimate = '~'
			self.duration = self.endyear - self.startyear
		self.meanyear = ((self.startyear + self.endyear) / 2)
		self.dynasty = dynasty
		if self.dynasty is None or self.dynasty == '':
			self.dynasty = dynasty_handler(startyear).name
		self.freq = 1 # this is added later from freqlist

class HYDCDUnicodeChar():
	def __init__(self, cid, entrycount, glyph, pinyin):
		self.id = cid
		self.glyph = glyph
		self.entrycount = entrycount
		self.pinyin = pinyin

class CBDBPerson(): # Person object type compatible with HYDCD word container
	def __init__(self, pid, name, startyear, endyear):
		self.id = pid
		self.cleanword = name
		self.length = len(name)
		self.book = 'CBDB'
		self.startyear = startyear
		self.endyear = endyear
		self.usecount = 0
		self.precision = 0
		if self.startyear == self.endyear: # we know the exact year
			self.estimate = ''
			self.duration = 1
		else: 
			self.estimate = '~'
			self.duration = self.endyear - self.startyear
		self.meanyear = ((self.startyear + self.endyear) / 2)
		self.dynasty = dynasty_handler(startyear).name
		self.freq = 1 # this is added later from freqlist

class LanguageModel():
	"A statistical language model with token counts, TE and tfidf."
	def __init__(self, chrononpath, freqfileprefix = '', mode = 'words', smoothing=0.5, modeltype='chronon'):
		self.name = PurePath(chrononpath).stem
		self.corpus_frequencies = pd.read_csv(chrononpath + mode + "totals.csv", index_col='item')
		print("🐼 Loading corpus frequencies for NLLR...")
		self.corpusdict = self.corpus_frequencies['freq'].to_dict()
		print("🐼 Loading temporal entropy...")
		self.tedict = self.corpus_frequencies['terel'].to_dict()

		self.chronons, self.chrondict, self.chrondict_tfidf, self.chrondict_idf, self.chrondims = {}, {}, {}, {}, {}
		for cfreqfile in sorted(glob.glob(chrononpath + freqfileprefix + mode + "_*.csv")):
			chronon = cfreqfile.replace(chrononpath + freqfileprefix + mode + "_", '').replace('.csv','')
			if modeltype == 'chronon':
				chronon = int(chronon)
			self.chronons[chronon] = pd.read_csv(cfreqfile, index_col='item')
			self.chrondict[chronon], self.chrondict_tfidf[chronon] = self.chronons[chronon]['freq'].to_dict(), self.chronons[chronon]['tfidf'].to_dict()
			self.chrondims[chronon] = len(self.chrondict[chronon])
			try:
				self.chrondict_idf[chronon] = self.chronons[chronon]['idf'].to_dict()
			except:
				self.chrondict_idf[chronon] = False

		self.longest_chronon = max(self.chrondims.items(), key=operator.itemgetter(1))[0]
		self.longchronminfreq = smoothing * min(self.chrondict[self.longest_chronon].values())
		# self.longchronminfreq = 0.00000001
		self.size = len(set().union(*(self.chrondict[c].keys() for c in self.chrondict.keys())))

class ResearchText():
	"Data container for texts to be analyzed"
	def __init__(self, textfile, punctuation, split=False, tradify=False, standardize=True):
		# keep a copy of the original for further use (like concordance)
		self.original = hanwithpunctuation(textfile.read())
		contains_simplified = simplifieddetector(self.original)
		if contains_simplified and tradify:
			self.original = mafan.tradify(self.original)
			contains_simplified = simplifieddetector(self.original)
		self.standardized = hydcd_standardize(self.original) if standardize == True else self.original

		self.filename = os.path.split(textfile.name)[1]
		if punctuation == False:
			self.text = [hanonly(self.standardized)]
		else:
			self.text = [self.standardized]
		self.length = len(self.text[0])
		self.chars = [list(self.text[0])]
		if split and self.length > split:
			self.text = [self.text[0][i:i+split] for i in range(0, self.length, split)]
			self.chars = [list(part) for part in self.text]
			self.partlengths = [len(part) for part in self.text]

	def print_concordance(self, lookup_type, width=64, limit=0):
		"Prints a concordance of given keyword in a text"
		half = (width - len(lookup_type)) // 2
		count = 0
		for pos in re.finditer(lookup_type, self.standardized):
			start = pos.start() - half
			end = pos.end() + half
			count +=1
			print("…" + self.standardized[start:pos.start()] + "  " + self.standardized[pos.start():pos.end()] + "  " + self.standardized[pos.end():end] + "…" + ' (pos.: ' + str(pos.start()) + ')')
			if limit > 0:
				if count >= limit:
					break

class TextFrequencies():
	"Data container for text frequency data"
	def __init__(self, text, settings = {}, index = 0, dictionary=None, relative=False, name='', verbose=True, filename=None, names=False, places=False):
		self.text = text
		self.ngrams, self.alltypes = [], {}
		self.name = name
			# generate the ngram lists we want
		for n in range(settings['MinGram'], settings['MaxGram']+1):
			if verbose: print(str(n) + "-grams... ", end='')
			# +1, because of python range implementation
			self.ngrams.extend(["".join(x) for x in list(find_ngrams(text.chars[index], n))])
			
			### temporary hack!
			# pd.DataFrame(FreqDist(["".join(x) for x in list(find_ngrams(text.chars[index], n))]).most_common()).to_csv(str(n) + "gram/" + filename, encoding='utf-8', index=False, sep='\t', header=False)

		self.unique_grams = set(self.ngrams)
		# if frequency list length is percentage, calculate desired length 
		if 'FreqListLength' not in settings: settings['FreqListLength'] = 1
		if 0 <= settings['FreqListLength'] <= 1:
			self.ngram_freqlist = FreqDist(self.ngrams).most_common(int(settings['FreqListLength'] * len(self.unique_grams)))
		else:
			self.ngram_freqlist = FreqDist(self.ngrams).most_common(int(settings['FreqListLength']))
		
		self.freq_dict = dict(self.ngram_freqlist)
		self.gramshapaxes = sum(map((1).__eq__, self.freq_dict.values())) / len(self.freq_dict)
		self.gramstypes = self.alltypes['grams'] = set(self.freq_dict.keys())
		self.gramstokencount = sum(self.freq_dict.values())
		self.gramstypecount = len(self.gramstypes)

		if relative:
			self.relfreq_dict = {gram: float(self.freq_dict[gram]) / self.gramstokencount for gram in self.gramstypes}

		if verbose: logging.info("📕 The text is " + str(text.length) + " characters long and has " + str(len(self.unique_grams)) + " different " + str(settings['MinGram']) + "-" + str(settings['MaxGram']) +"-grams.")
		if verbose: logging.info("(" + str(len(self.unique_grams) * 100000 / text.length) + " different n-grams per 100.000 characters in the text.)")
		if verbose: logging.info("✅ A list of the " + str(len(self.ngram_freqlist)) + " most common " + str(settings['MinGram']) + "–" + str(settings['MaxGram']) + "-漢字-grams in the text was computed.")

		if dictionary:
			self.wordtypes = self.alltypes['words'] = self.gramstypes & dictionary
			self.wordstypecount = len(self.wordtypes)
			self.wordsfreq_dict = {word: self.freq_dict[word] for word in self.wordtypes}
			self.wordshapaxes = sum(map((1).__eq__, self.wordsfreq_dict.values())) / len(self.wordsfreq_dict)
			self.wordstokencount = sum(self.wordsfreq_dict.values())
			if relative:
				self.wordsrelfreq_dict = dict((w, float(f) / self.wordstokencount) for w, f in self.wordsfreq_dict.items())
			if verbose: logging.info("📕 The text contains %s word types with a total of %s word tokens." % (len(self.wordtypes), self.wordstokencount))

		if names:
			self.nametypes = self.alltypes['names'] = self.gramstypes & names
			self.nametypecount = len(self.nametypes)
			if len(self.nametypes) > 0:
				self.namefreq_dict = {name: self.freq_dict[name] for name in self.nametypes}
				self.nametokencount = sum(self.namefreq_dict.values())
			else:
				logging.info("❎ No person names work to with.")
				self.namefreq_dict, self.nametokencount = {}, 0
				self.nametokencount = 0
			if relative:
				self.namerelfreq_dict = dict((p, float(f) / self.nametokencount) for p, f in self.namefreq_dict.items())
			if verbose: logging.info("📕 The text contains %s name types with a total of %s possible person name tokens." % (len(self.nametypes), self.nametokencount))
		else:
			self.nametypes = {}

		if places:
			self.placetypes = self.alltypes['places'] = self.gramstypes & places
			self.placetypecount = len(self.placetypes)
			if len(self.placetypes) > 0:
				self.placefreq_dict = {name: self.freq_dict[name] for name in self.placetypes}
				self.placetokencount = sum(self.placefreq_dict.values())
			else:
				logging.info("❎ No place names work to with.")
				self.placefreq_dict, self.placetokencount = {}, 0
				self.placetokencount = 0
			if relative:
				self.placerelfreq_dict = dict((p, float(f) / self.placetokencount) for p, f in self.placefreq_dict.items())
			if verbose: logging.info("📕 The text contains %s place name types with a total of %s possible place name tokens." % (len(self.placetypes), self.placetokencount))
		else:
			self.placetypes = {}
		
		self.freq_grams = set([x[0] for x in self.ngram_freqlist if x[1] >= settings['LookupMinimumNgramCount']])
		self.freqlistlength = len(self.freq_grams)

	def extract_frequent_words(self, dictionary, n):
		word_freqlist = []
		bar = ShadyBar('Checking frequent n-grams for words.', max=n, width=60)
		for word, freq in self.ngram_freqlist:
			if word in dictionary:
				word_freqlist.append((word, freq))
				bar.next()
			if len(word_freqlist) == n:
				break
		bar.finish()
		freq_words = set([x[0] for x in word_freqlist])
		return(freq_words)

	def export_grams(self, mingram, maxgram):
		for n in range(mingram, maxgram+1):
			ngrams = {k: v for k, v in self.freq_dict.items() if len(k) == n}
			grampath = str(n) + 'gram'
			try:
				os.makedirs(grampath)
			except:
				pass
			with open(grampath + '/' + self.name + '.txt', 'w') as f:
				for gr, fr in ngrams.items():
					f.write("%s\t%s\n" % (gr, fr))

class Giftschrank():
	def __init__(self, name='difangzhi-grams'):
		try:
			lines = list(loadtxt("primary_sources/" +  name + "/giftschrank.txt", dtype=str, comments="#", unpack=False))
		except:
			lines = []
		self.name = name
		self.schrank = set(lines)

	def im_schrank(self, textid):
		if textid in self.schrank:
			return True
		else:
			return False

	def in_schrank(self, textid):
		if textid not in self.schrank:
			with open("primary_sources/" +  self.name + "/giftschrank.txt", "a") as file:
				file.write('\n' + textid)
			self.schrank.add(textid)

class TimeMatch():
	def __init__(self, match):
		self.book = 'DDBC'
		self.expression = self.cleanword = match.group(0) #同光二十年春癸未
		self.length = len(self.expression)
		self.era_name = match.group(1)
		self.type = "e"
		self.estimate = ''
		self.era_year = False
		self.startyear, self.endyear, self.dynasty, self.emperor = False, False, False, False
		self.freq = 1

		try:
			if "年" in match.captures(4) or "載" in match.captures(4):
				self.type = "y"
				try:
					if "元" in match.captures(3):
						self.era_year = 1
					else:
						self.era_year = pycnnum.cn2num(match.captures(3)[0])
				except:
					self.era_year = False
		except:
			self.era_year = False

		try:
			if "月" in match.captures(4):
				self.type = "m"
				if "日" in match.captures(4): 	# if there is also a day given as in 九日, we will have another capture
					try: # Consider MXBT 應順元年四月九日己卯
						self.month = "閏" + match.captures(3)[1] if "閏" in match.group(0) else match.captures(3)[1]
					except:
						self.month = False
				else: # if 日 is not included, we can use last capture from group3 as month
					try: 
						self.month = "閏" + match.group(3) if "閏" in match.group(0) else match.group(3)
					except:
						self.month = False

		except:
			self.month = False
		try: 
			self.season = match.group(5)
		except:
			self.season = False
		try:
			self.tiangan = match.group(6)
		except:
			self.tiangan = False

	def __str__(self):
		return(self.expression)

	def sql(self): # select for time expression match object
		sql = ("""select m.id, m.year, m.month_name, ceil((m.first-1721424.5)/365.25) as startyear, ceil((m.last-1721424.5)/365.25) as endyear, d.type,
		m.ganzhi, en.name as era_name, hm.name as emperor, dn.name as dynasty 
		from ddbc_time.t_month m
		left join ddbc_time.t_era e on e.id = m.era_id
		left join ddbc_time.t_era_names en on e.id = en.`era_id`
		left join ddbc_time.t_emperor h on e.`emperor_id` = h.id
		left join ddbc_time.t_emperor_names hm on h.id = hm.`emperor_id`
		left join ddbc_time.t_dynasty d on h.`dynasty_id` = d.id
		left join ddbc_time.t_dynasty_names dn on d.`id` = dn.`dynasty_id`
		where en.name = '%s' """) % (self.era_name)
		if self.era_year:
			sql += "and year = %s " % (self.era_year)
		sql += """and type = 'chinese'
			group by e.id, d.id
			order by m.era_id, m.year, m.`month`""" 
		return(sql)

	def meanyear(self):
		try:
			return((self.startyear + self.endyear) / 2)
		except:
			print("No mean year for %s." % self.expression)
			return(False)

	def duration(self):
		try:
			if self.startyear == self.endyear: # we know the exact year
				return(1)
			else: 
				return(self.endyear - self.startyear)
		except:
			return(False)


class PennCTBText():
		"Object with tokens from the segmented Penn Chinese Treebank"
		def __init__(self, xmlfile):
			self.original = xmlfile.read()
			self.soup = BeautifulSoup(self.original, "xml")
			sentences = self.soup.find_all('S')
			self.plain, self.tokens = "", []
			for sentence in sentences:
				for strng in sentence.stripped_strings:
					self.plain += strng.replace(" ", "")
					for s in strng.split():
						self.tokens.append(s)
			self.words = filter(lambda w: not punctuation.search(w), self.tokens)
			self.wordsndots = filter(lambda w: not ik_punctuation.search(w), self.tokens)

class SheffieldText():
		"Object with tokens from a Sheffield Corpus XML"
		def __init__(self, xmlfile):
			self.original = xmlfile.read()
			# print(self.original)
			self.soup = BeautifulSoup(self.original, "lxml") # use lxml to ensure conversion/decoding of HTML entities to Unicode
			for sp in self.soup.find_all('set_phrase'):
				this_content = "".join(sp.stripped_strings)
				sp.clear()
				sp.string = this_content
			for poly in self.soup.find_all(type=re.compile("polysyllabic")):
				this_content = "".join(poly.stripped_strings)
				poly.clear
				poly.string = this_content
			sentences = self.soup.find_all('s')
			self.plain, self.tokens = "", []
			for sentence in sentences:
				for string in sentence.stripped_strings:
					self.plain += string
					self.tokens.append(string)
			self.words = filter(lambda w: not punctuation.search(w), self.tokens)
			self.wordsndots = filter(lambda w: not ik_punctuation.search(w), self.tokens)

class SinicaText():
		"Object with tokens from a Sinica Corpus txt"
		def __init__(self, textfile):
			self.original = textfile.read()
			self.plain, self.tokens = "", []
			fix1, fix2 = re.compile('\([^\)]+\)'), re.compile('\[[^\]]+\]')
			text = fix1.sub('|', self.original)
			text = fix2.sub('', text)
			text = punctuation.sub('|\g<0>|', text)
			text = text.replace("||","|").split('|')
			for string in text:
				self.plain += string
				self.tokens.append(string)
			self.words = filter(lambda w: not punctuation.search(w), self.tokens)
			self.wordsndots = filter(lambda w: not ik_punctuation.search(w), self.tokens)
