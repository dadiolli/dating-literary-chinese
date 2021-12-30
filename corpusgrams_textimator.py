"""Run a lexicographic time depth estimation on a corpus selection of CrossAsia ngrams.
   Can also be used to calculate AYL dating or train AYL models by using list of WordFreqListLength in settings."""

###########################################################
# Import external modules
###########################################################

import argparse, glob, inspect, logging, math, matplotlib.pyplot as plt
import multiprocessing as mp, numpy as np, pandas as pd, random, os, sys, time
from datetime import datetime
from progress.bar import ShadyBar

###########################################################
# Import own modules
###########################################################

from modules.classes3 import CAGrams, Giftschrank, PlainTextCorpus
from modules.neologism_profiler import neologism_profiler_grams
from modules.settings3 import settingprinter, settings_dfz3 as settings
from modules.toolbox3 import mae
#from modules.settings3 import settingprinter, settings_ayl_plain_trained as settings
from modules.visualizations import export_barplot
from modules.initialize_logger3 import *


# DFZ 216 test run
# settings['Sample'] = '../hydcd2017/results/guidefuzhi_example.csv' # example
settings['Sample'] = '../hydcd2017/results/chronon_observations_difangzhi-gramswords_1to2_20201205-114042.csv' # DFZ216
exclude_file = '../hydcd2017/results/dfz_training_432.csv' # training for AYL model
exclude_meta = pd.read_csv(exclude_file, index_col='filename') # get meta data
corpus = CAGrams('difangzhi-grams', 'difangzhi-metadata.xlsx', settings['Sample'], exclude = exclude_meta.index, minchronon = -700)

# DFZ 432 training run, excluded DFZ216
# settings['Sample'] = '../hydcd2017/results/dfz_training_432.csv' # training for AYL model
# # corpus = CAGrams('difangzhi-grams', 'difangzhi-metadata.xlsx', settings['Sample'], minchronon = -700)
# exclude_file = '../hydcd2017/results/chronon_observations_difangzhi-gramswords_1to2_20201205-114042.csv' # DFZ216
# exclude_meta = pd.read_csv(exclude_file, index_col='filename') # get meta data
# corpus = CAGrams('difangzhi-grams', 'difangzhi-metadata.xlsx', settings['Sample'], exclude = exclude_meta.index, minchronon = 1300)

# ZHENGSHI 25 
# settings['Sample'] = 25
# corpus = CAGrams('zhengshi-grams', 'zhengshi-metadata.xlsx', settings['Sample'])
# corpus = PlainTextCorpus('zhengshi2', 'primary_sources/zhengshi2-corpus')
# COMBINED LOEWE ZHENGSHI 
# settings['Sample'] = 73
# corpus = PlainTextCorpus('combined2-corpus', 'primary_sources/combined2-corpus')


# XXSKQS
# Version mit 105 Texten # settings['Sample'] = 'results/chronon_observations_xx-skqs-gramschronons_allquotes_12_timewords_1to2_20210113-163331.csv'
# settings['Sample'] = '../hydcd2017/results/chronon_observations_xx-skqs-gramschronons_xxskqs_12_times_normwords_1to2_20210726-101039.csv' # 176 Texte (wie in XXSKQS chronon vs. documents)
# corpus = CAGrams('xx-skqs-grams', 'xuxiu_metadata_year.xlsx', settings['Sample'], minchronon = -700)

# settings['Sample'] = 'results/chronon_observations_difangzhi-gramswords_1to2_20191218-150319_STAGE.csv'

# 2020-06-13 need to run a sample from the training data to check, whether training was meaningful!
# settings['Sample'] = 'results/dfz_training_testsample100.csv'

# method_description = inspect.getsource(smoothedsimplechroner)
# logging.debug(str(method_description))

observationfile = 'textimator_observations_' + corpus.name + '_' + str(settings['MinGram']) + 'to' + str(settings['MaxGram'])

def simplechron_task(source):
	i, sourcefile, timepath = source
	logging.warning("🐍 Running Profiler on %s (file: %s), pass %s of %s." % (corpus.sample.dc_title[sourcefile], sourcefile, i+1, len(corpus.sample.index)))
	# corpus.sample.to_csv(timepath+'dfz_training_432.csv')
	observation, profile = neologism_profiler_grams(sourcefile, settings, corpus)
	resultmoji = "🆗 " if observation.simplechronerhit[sourcefile] == True else "⚠️ "
	logging.warning("%s Simplechron + names dated to %s–%s. %s years from %s." % (resultmoji, observation.simplechrononer[sourcefile], observation.simplechrononer[sourcefile] + 100, (observation.simplechrononer[sourcefile] + 50) - observation.known_year[sourcefile], observation.known_year[sourcefile]))
	profile.to_csv(timepath +  'raw/' + sourcefile + '_' + observationfile + '.csv', encoding='utf-8', index=True)
	return(observation)

def main(timepath):
	# initialize_logger("multi_textimator.log", logpath=timepath)
	work, gs = [], Giftschrank()
	for i, sourcefile in enumerate(corpus.sample.index):
		faulty = gs.im_schrank(sourcefile)
		if not faulty: work.append((i, sourcefile, timepath)) 

	pool = mp.Pool(mp.cpu_count()-3)
	results = pool.map(simplechron_task, work)
	pool.close()

	observations = pd.concat(results)
	observations.to_excel(timepath + observationfile + '.xlsx', encoding='utf-8', index=True, index_label='source')
	logging.warning("\n🐼 Results saved to %s%s.xlsx" % (timepath, observationfile))
	logging.warning("🐼 Method: simplechron %.3f correct, %.3f too new, %.3f too old." % (observations.plainsimplechronhit[observations.plainsimplechronhit==True].count() / len(observations.index), observations.plainsimplechron[observations.plainsimplechron > observations.known_century].count() / len(observations.index), observations.plainsimplechron[observations.plainsimplechron < observations.known_century].count() / len(observations.index)))
	#logging.warning("🐼 simplechron medium distance to known year was %.3f, max distance was %.3f." % (abs(observations.known_year-(observations.plainsimplechron+50)).mean(), abs(observations.known_year-(observations.plainsimplechron+50)).max()))
	logging.warning("🐼 simplechron medium distance to known year was %.3f, max distance was %.3f." % (mae(observations, 'known_year', 'plainsimplechron', 100), abs(observations.known_year-(observations.plainsimplechron+50)).max()))
	logging.warning("🐼 Method: s-smoothed simplechron %.3f correct, %.3f too new, %.3f too old." % (observations.piotsimplechronhit[observations.piotsimplechronhit==True].count() / len(observations.index), observations.piotsimplechron[observations.piotsimplechron > observations.known_century].count() / len(observations.index), observations.piotsimplechron[observations.piotsimplechron < observations.known_century].count() / len(observations.index)))
	#logging.warning("🐼 s-smoothed simplechron medium distance to known year was %.3f, max distance was %.3f." % ( abs(observations.known_year-(observations.piotsimplechron+50)).mean(), abs(observations.known_year-(observations.piotsimplechron+50)).max()))
	logging.warning("🐼 s-smoothed simplechron medium distance to known year was %.3f, max distance was %.3f." % ( mae(observations, 'known_year', 'piotsimplechron', 100), abs(observations.known_year-(observations.piotsimplechron+50)).max()))
	logging.warning("🐼 Method: smoothed simplechron %.3f correct, %.3f too new, %.3f too old." % (observations.simplechronhit[observations.simplechronhit==True].count() / len(observations.index), observations.simplechron[observations.simplechron > observations.known_century].count() / len(observations.index), observations.simplechron[observations.simplechron < observations.known_century].count() / len(observations.index)))
	# logging.warning("🐼 Smoothed Simplechron medium distance to known year was %.3f, max distance was %.3f." % ( abs(observations.known_year-(observations.simplechron+50)).mean(), abs(observations.known_year-(observations.simplechron+50)).max()))
	logging.warning("🐼 Smoothed Simplechron medium distance to known year was %.3f, max distance was %.3f." % ( mae(observations, 'known_year', 'simplechron', 100), abs(observations.known_year-(observations.simplechron+50)).max()))
	logging.warning("🐼 Method: simplechron + NER %.3f correct, %.3f too new, %.3f too old." % (observations.simplechronerhit[observations.simplechronerhit==True].count() / len(observations.index), observations.simplechrononer[observations.simplechrononer > observations.known_century].count() / len(observations.index), observations.simplechrononer[observations.simplechrononer < observations.known_century].count() / len(observations.index)))
	# logging.warning("🐼 Simplechron + NER medium distance to known year was %.3f, max distance was %.3f." % ( abs(observations.known_year-(observations.simplechrononer+50)).mean(), abs(observations.known_year-(observations.simplechrononer+50)).max()))
	logging.warning("🐼 Simplechron + NER medium distance to known year was %.3f, max distance was %.3f." % ( mae(observations, 'known_year', 'simplechrononer', 100), abs(observations.known_year-(observations.simplechrononer+50)).max()))
	logging.warning("🐼 Method: Latest date %.3f correct, %.3f too new, %.3f too old." % (observations.ndt_hit[observations.ndt_hit==True].count() / len(observations.index), observations.ndt_hit[observations.ndt_dated > observations.known_century].count() / len(observations.index), observations.ndt_hit[observations.ndt_dated < observations.known_century].count() / len(observations.index)))	
	# logging.warning("🐼 Latest date medium distance to known year was %.3f, max distance was %.3f." % ( abs(observations[observations.ndt_dated != False].known_year-(observations[observations.ndt_dated != False].ndt_dated+50)).mean(), abs(observations[observations.ndt_dated != False].known_year-(observations[observations.ndt_dated != False].ndt_dated+50)).max()))
	logging.warning("🐼 Latest date medium distance to known year was %.3f, max distance was %.3f." % ( mae(observations[observations.ndt_dated != False], 'known_year', 'ndt_dated', 100), abs(observations[observations.ndt_dated != False].known_year-(observations[observations.ndt_dated != False].ndt_dated+50)).max()))
	logging.warning("🐼 Method: simplechron + NER + latest date (combochron) %.3f correct, %.3f too new, %.3f too old." % (observations.combochronhit[observations.combochronhit==True].count() / len(observations.index), observations.combochronon[observations.combochronon > observations.known_century].count() / len(observations.index), observations.combochronon[observations.combochronon < observations.known_century].count() / len(observations.index)))
	# logging.warning("🐼 Combochron medium distance to known year was %.3f, max distance was %.3f." % ( abs(observations.known_year-(observations.combochronon+50)).mean(), abs(observations.known_year-(observations.combochronon+50)).max()))
	logging.warning("🐼 Combochron medium distance to known year was %.3f, max distance was %.3f." % ( mae(observations, 'known_year', 'combochronon', 100), abs(observations.known_year-(observations.combochronon+50)).max()))

	
	###########################################################
	# Export results
	###########################################################

	# need to run a cycle to create plots
	bar = ShadyBar('Plotting.', max=len(observations.index), width=60)
	for o in observations.index:
		profile = pd.read_csv(timepath +  'raw/' + o + '_' + observationfile + '.csv', encoding='utf-8', index_col=0)
		# export_barplot(profile, 'piotrowskismoothed', "Word types (s-corrected)", observations.loc[o], exportpath=timepath + '/ssmoothed/')
		export_barplot(profile, 'smoothed', "Word types (linear-corrected)", observations.loc[o], exportpath=timepath + '/smoothed/')
		# export_barplot(profile, 'count', "Word types", observations.loc[o], exportpath=timepath + '/plain/')
		bar.next()
	bar.finish()

	sys.stderr.write("\a\a\n")


if __name__ == '__main__':
	timepath = 'results/%s/' % (datetime.now().strftime('%Y%m%d-%H%M%S'))
	os.mkdir(timepath); os.mkdir(timepath + '/raw');
	os.mkdir(timepath + '/plain'); os.mkdir(timepath + '/smoothed'); 
	# os.mkdir(timepath + '/ssmoothed');
	initialize_logger("multi_textimator.log", loglevel=logging.INFO, logpath=timepath)
	logging.warning("🐼 Got metadata for %s texts, sample: %s" % ((len(corpus.sample)), settings['Sample']))
	settingprinter(settings)
	main(timepath)