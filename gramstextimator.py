"Run lexicographic time depth estimation on single file of CrossAsia ngrams."

###########################################################
# Import external modules
###########################################################

import argparse, inspect, math, matplotlib.pyplot as plt, multiprocessing as mp, pandas as pd, os, sys, time
from datetime import datetime
from progress.bar import ShadyBar

###########################################################
# Import own modules
###########################################################

from modules.classes3 import CAGrams
from modules.neologism_profiler import neologism_profiler_grams
# from modules.neologism_profiler import smoothedsimplechroner # only for logging purpose
# from modules.settings3 import settingprinter, settings_dfz as settings
from modules.settings3 import settingprinter, settings_dfz3 as settings
from modules.visualizations import export_barplot
from modules.initialize_logger3 import *

###########################################################
# Initialize
###########################################################

timepath = 'results/' + datetime.now().strftime('%Y%m%d-%H%M%S') + '/'
os.mkdir(timepath); os.mkdir(timepath + '/raw')
initialize_logger("dfz_textimator.log", logpath=timepath)

# sourcefile = 'a3a8b385c6387f3f24b83a8966457198'
sourcefile = '0c87f43d7392c0589fbfb491e5165af9'

settings['UseDFZTraining'] = True
settings['UseCBDB'], settings['UseCBDBPlaces'] = True, True

corpus = CAGrams('difangzhi-grams', 'difangzhi-metadata.xlsx', minchronon = -700)
logging.info("🐼 Got metadata for %s texts" % ((len(corpus.metadata))))

observationfile = 'textimator_observations_' + corpus.name + '_' + str(settings['MinGram']) + 'to' + str(settings['MaxGram'])

settingprinter(settings)
#method_description = inspect.getsource(smoothedsimplechroner)
#logging.info(str(method_description))

###########################################################
# Loop through parts of the input text
###########################################################

def simplechron_task(source):
	i, sourcefile = source
	logging.info("🐍 Running Profiler on %s (file: %s)." % (corpus.metadata.dc_title[sourcefile], sourcefile))
	observation, profile = neologism_profiler_grams(sourcefile, settings, corpus)
	resultmoji = "🆗 " if observation.simplechronerhit[sourcefile] == True else "⚠️ "
	logging.info("%s Simplechron + names dated to %s–%s. %s years from %s." % (resultmoji, observation.simplechrononer[sourcefile], observation.simplechrononer[sourcefile] + 100, (observation.simplechrononer[sourcefile] + 50) - observation.known_year[sourcefile], observation.known_year[sourcefile]))
	profile.to_csv(timepath +  'raw/' + sourcefile + '_' + observationfile + '.csv', encoding='utf-8', index=True)
	return(observation)
	
###########################################################
# Export results
###########################################################

results = [simplechron_task((0, sourcefile))]
observations = pd.concat(results)
observations.to_excel(timepath + observationfile + '.xlsx', encoding='utf-8', index=True, index_label='source')
logging.info("\n🐼 Results saved to %s%s.xlsx" % (timepath, observationfile))
logging.info("🐼 Method: simplechron %.2f correct, %.2f too new, %.2f too old." % (observations.simplechronhit[observations.simplechronhit==True].count() / len(observations.index), observations.simplechron[observations.simplechron > observations.known_century].count() / len(observations.index), observations.simplechron[observations.simplechron < observations.known_century].count() / len(observations.index)))
logging.info("🐼 Method: simplechron + NER %.2f correct, %.2f too new, %.2f too old." % (observations.simplechronerhit[observations.simplechronerhit==True].count() / len(observations.index), observations.simplechrononer[observations.simplechrononer > observations.known_century].count() / len(observations.index), observations.simplechrononer[observations.simplechrononer < observations.known_century].count() / len(observations.index)))
logging.info("🐼 Simplechron + NER medium distance to known year was %.2f." % ( abs(observations.known_year-(observations.simplechrononer+50)).mean()))

# need to run a cycle to create plots
bar = ShadyBar('Plotting.', max=len(observations.index), width=60)
for o in observations.index:
	profile = pd.read_csv(timepath +  'raw/' + o + '_' + observationfile + '.csv', encoding='utf-8', index_col=0)
	export_barplot(profile, 'smoothed', "Word types (smoothed)", observations.loc[o], exportpath=timepath)
	bar.next()
bar.finish()

sys.stderr.write("\a\a\n")