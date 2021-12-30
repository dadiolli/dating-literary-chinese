""" 
Holds different setting for different purposes.
Holds methods for printing and streamlining settings.
"""

import logging
from collections import defaultdict

# setting printer serves as implicit documentation
def settingprinter(settings):
	logging.info("ℹ️  Current Settings: Checking %s-%s-grams." % (settings['MinGram'], settings['MaxGram']))
	if settings['FreqListLength'] <= 1:
		logging.info("\t\t\tUsing %s percent most frequent types." % (settings['FreqListLength'] * 100))
	else:
		logging.info("\t\t\tUsing %s most frequent types." % (settings['FreqListLength']))
	logging.info("\t\t\tPunctuation remains in the text: %s." % (settings['Punctuation']))
	if 'ExcludeSelf' in settings:
		logging.info("\t\t\tExcluding words from input text: %s." % (settings['ExcludeSelf']))
	if 'UseNonHYDCDEvidence' in settings:
		logging.info("\t\t\tUsing evidence from Loewe and zhengshi corpus training data: %s." % (settings['UseNonHYDCDEvidence']))
	if 'UseDFZTraining' in settings:
		logging.info("\t\t\tUsing evidence from Difangzhi n-gram corpus training data: %s." % (settings['UseDFZTraining']))
	if 'Split' in settings:
		if settings['Split'] > 0:
			logging.info("\t\t\tChunking into parts of %s characters, omitting remainder." % (settings['Split']))
	logging.info("\t\t\tUsing CBCB as NER database for person names: %s." % (settings['UseCBDB']))
	logging.info("\t\t\tUsing CBCB as NER database for place names: %s." % (settings['UseCBDBPlaces']))

def standardize_settings(input_settings=dict()):
	standard_settings = defaultdict(lambda : False)
	# no need to set 
	# 'ListOutput', # Output the Frequency distribution list of the input
	# 'NeologismByText', # Output the list of neologisms per locus classicus 
	# 'NeologismByDynasty', # print word type output by lexeme dynasty
	# 'PrintConcordance', 
	# 'ExcludeSelf', # exclude neoligisms from this text (need to know clearbook name of the text) 
	# 'Split', # run everything on chunks of this length, not for n-gram lists!
	# 'StatisticsOutputDynasties', # print output by dynasties
	# 'WordFreqListLength' # set a limit (rel. or abs.) for amount of word types to be considered

	standard_settings.update(input_settings)
	# make sure standard values are available
	defaults = [('ChrononMethods', []),
				('MinGram', 2),
                ('MaxGram', 4),
                ('FreqListLength', 1), # How many items to use from the ngram list, standard for regression method 0.015, 1 = 100 %
                ('LookupMinimumNgramCount', 1), # how frequent do we want an n-gram to be to look it up later?
                ('Punctuation', True), # True: leave it as is
                ('StatisticsOutput', True),
                ('ConcordanceSize', 3),
                ('ConcordanceSentenceLength', 64),
                ('UseNonHYDCDEvidence', True),
                ('UseDFZTraining', True),
                ('UseCBDB', True),
                ('UseCBDBPlaces', True),
                ('UseTimeExpr', True),
                ('HYDCDStandardize', False),
                ('PrintConcordance', False)
                ]
	for key, defv in defaults:
		standard_settings.setdefault(key, defv)
	return standard_settings


def compare_settings(local, model, mode="slm"):
	"Compare settings from current run to the original model settings."
	problems = ''
	if local['MinGram'] != model['MinGram']:
		problems += '❌ Caution, model minimum n-gram length is %s \n' % model['MinGram']
	if local['MaxGram'] != model['MaxGram']:
		problems += '❌ Caution, model maximum n-gram length is %s \n' % model['MaxGram']
	if local['UseCBDB'] != model['UseCBDB'] or local['UseCBDBPlaces'] != model['UseCBDBPlaces']:
		problems += '❌ Caution, model NER settings do not match current settings. \n'
	if local['UseTimeExpr']	!= model['UseTimeExpr']:
		problems += '❌ Caution, model time expression settings do not match current settings. \n'
	if local['HYDCDStandardize'] != model['HYDCDStandardize']:
		problems += '❌ Caution, model character normalization settings do not match current settings. \n'
	if mode == 'slm':
		if local['BaseChronon']	!= model['HistoryStart']:
			problems += 'ℹ️ Base chronon setting does not match model start. \n'
		if local['ChrononDuration']	!= model['Chronon']:
			problems += '❌ Chronon duration incompatible with given model. \n'
		try:
			if local['ModelType'] != model['ModelType']:
				problems += '❌ Language model type (chronon / document) mismatch! \n'
		except:
			pass
	if problems == '':
		problems = '✅ Model settings seem compatible with current settings. \n'
	return problems

settings_default = standardize_settings(dict())
settings_chronon = {
	'ChrononPath': 'chronons_allquotes',
	'ChrononMethods': ['kld-te', 'nllr-te', 'rand'],
	'ChrononModel': 'words',
	'UseTimeExpr': True
	}
settings_chronon = standardize_settings(settings_chronon)

settings_1to4 = {
	'MinGram': 1,
	'FreqListLength': 20000, # How many items to use from the ngram list, standard for regression method 0.015?
	}
settings_1to4 = standardize_settings(settings_1to4)

settings_dfz = {
	'MinGram': 1,
	'MaxGram': 2,
	'FreqListLength': 1, # 
	'Punctuation': False, # True: leave it as is
	}	
settings_dfz = standardize_settings(settings_dfz)	

settings_dfz3 = {
	'MinGram': 2,
	'MaxGram': 3,
	'UseNonHYDCDEvidence': True,
	'UseDFZTraining': True,
	'HYDCDStandardize': True,
	'UseCBDB': True,
	'UseTimeExpr': True,
	# 'WordFreqListLength': [0.01, 0.05, 0.1, 0.25, 0.5, 0.8, 1, 100, 250, 500, 1000, 2000, 5000, 10000]
	# 'WordFreqListLength': [0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1, 100, 250, 500, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 11000, 12000, 13000]
	# 'WordFreqListLength': [0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1]
	'WordFreqListLength': [1]
	}		
settings_dfz3 = standardize_settings(settings_dfz3)		

settings_corpuscounts = {
	'MinGram': 1,
	'MaxGram': 1,
	'UseNonHYDCDEvidence': False,
	'UseDFZTraining': False,
	'HYDCDStandardize': False,
	'UseCBDB': False,
	'UseTimeExpr': False,
	}		
settings_corpuscounts = standardize_settings(settings_corpuscounts)		


settings_ayl_plain = {
	'MinGram': 2,
	'MaxGram': 4,
	'UseNonHYDCDEvidence': False,
	'UseDFZTraining': False,
	'HYDCDStandardize': True,
	'UseCBDB': True,
	'UseTimeExpr': True,
	'WordFreqListLength': [0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1]
	}		
settings_ayl_plain = standardize_settings(settings_ayl_plain)		

settings_ayl_plain_trained = {
	'MinGram': 2,
	'MaxGram': 4,
	'UseNonHYDCDEvidence': True,
	'UseDFZTraining': True,
	'HYDCDStandardize': True,
	'UseCBDB': True,
	'UseTimeExpr': True,
	'WordFreqListLength': [0.01, 0.025, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1]
	}		
settings_ayl_plain_trained = standardize_settings(settings_ayl_plain_trained)		

settings_split = {
	'FreqListLength': 0.05, # How many items to use from the ngram list, standard 0.05
	'Split': 100000
	}
settings_split = standardize_settings(settings_split)	

settings_trainer = {
	'MinGram': 1,
	'MaxGram': 4,
	'HYDCDStandardize': True,
	'UseNonHYDCDEvidence': True
	}
settings_trainer = standardize_settings(settings_trainer)

settings_all = {
	'StatisticsOutput': True,
	'NeologismByDynasty': True, # Output the list of neologisms per dynasty
	'UseDFZTraining': False,
	'UseNonHYDCDEvidence': False,
	'HYDCDStandardize': True,
	'UseTimeExpr': True,
	'ListOutput': True,
	'PrintConcordance': True,
	'ConcordanceSentenceLength': 32,
	'WordFreqListLength': [0.15, 1]
	}
settings_all = standardize_settings(settings_all)	

settings_single = {
	'MinGram': 2,
	'MaxGram': 4,
	'StatisticsOutput': True,
	'UseDFZTraining': True,
	'UseNonHYDCDEvidence': True,
	'HYDCDStandardize': True,
	'ListOutput': False,
	'PrintConcordance': False,
	'ConcordanceSentenceLength': 32,
	'WordFreqListLength': [0.9],
	'ChrononMethods': ['nllr'], # ['nllr', 'nllr-te'], 
	'ChrononModel': 'words',
	'ChrononPath': 'chronons_allquotes_12_time',
	'UseTimeExpr': True
	}
settings_single = standardize_settings(settings_single)	

settings_all_list = {
	'ListOutput': True, # Output the Frequency distribution list of the input
	'NeologismByText': True, # Output the list of neologisms per locus classicus 
	'PrintConcordance': True, # want to have a concordance for each word? - only with ListOutput
	}
settings_all_list = standardize_settings(settings_all_list)	

settings_maximal = {
	'FreqListLength': 0.05, # How many items to use from the ngram list, standard 0.05
	'StatisticsOutput': True,
	'StatisticsOutputDynasties': True,
	'ListOutput': True, # Output the Frequency distribution list of the input
	'NeologismByText': True, # Output the list of neologisms per locus classicus 
	'NeologismByDynasty': True, # Output the list of neologisms per dynasty
	'PrintConcordance': True, # want to have a concordance for each word? - only with ListOutput
	}
settings_maximal = standardize_settings(settings_maximal)		

settings_minimal = {
	'FreqListLength': 0.015, # How many items to use from the ngram list, standard 0.05
	}
settings_minimal = standardize_settings(settings_minimal)	
