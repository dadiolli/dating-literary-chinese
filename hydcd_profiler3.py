"""
Calculate the HYDCD bias adjustment factors for given settings.
Need separate factors for 1–2, 1–3, 1–4, 2–3, 2–4 gram words.
Can be calculated with and without additional corpus training data.
s-correction factors (assuming an s-shaped growth of the Chinese lexicon)
need to be calculated in R using the drm function of the drc package like so:
# begin R source here // can be automated using rpy2 
library(drc)
lexicalization <- read.csv("hydcd/profile_NonHYDCD_False_UseDFZ_False_Min_2_Max_4__predict_piotrowski.csv", encoding="UTF-8", header=TRUE, row.names=NULL, sep=",");
vocabulary_growth.hydcdmodel <- drm(cumsum(lexicalization$poly) ~ lexicalization$century, fct=L.3(fixed=c(NA, NA, NA)), data = lexicalization)
summary(vocabulary_growth.hydcdmodel)
fun.s <- function(x) { predict(vocabulary_growth.hydcdmodel, newdata = data.frame(x)) }
lexicalization$prediction <- predict(vocabulary_growth.hydcdmodel)
starter <- lexicalization$count[0]
lexicalization$model <- c(0, diff(lexicalization$prediction))
lexicalization$piotweight <- lexicalization$model / lexicalization$poly
lexicalization[1, "piotweight"] <- 1.0
# export = subset(lexicalization, select = -c(typelist)) # use if the typelist was generated for the HYDCD profile in order to avoid large files
write.csv(lexicalization,"hydcd/profile_NonHYDCD_False_UseDFZ_False_Min_2_Max_4__predict_piotrowski.csv", row.names = FALSE)
"""

###########################################################
# load python and own modules and get prepared
###########################################################

import numpy as np, pandas as pd, sys, time

from collections import defaultdict, Counter, OrderedDict
from itertools import starmap
from progress.bar import ShadyBar
from modules.classes3 import HYDCDWord
from modules.dynasties3 import hydcd_dynasties, century_dict, dynasty_handler
from modules.initialize_logger3 import *
from modules.settings3 import standardize_settings, settingprinter
from modules.toolbox3 import database_connect, select_builder # terminal_statistics
from modules.neologism_profiler import profile_worker

###########################################################
# get and prepare dynasty information
###########################################################

if __name__ == "__main__":
	initialize_logger("hydcd_profiler.log")

start_time = time.time()
logging.info('🐍 Creating HYDCD neologism profiles.')
settings = {
	'MinGram': 2,
	'MaxGram': 4,
	'UseNonHYDCDEvidence': True,
	'UseDFZTraining': True,
	'Punctuation': True
	}

settings = standardize_settings(settings)	
settingprinter(settings)

filenamer =  "hydcd/profile_NonHYDCD_" + str(settings['UseNonHYDCDEvidence']) + "_UseDFZ_" + str(settings['UseDFZTraining']) + "_Min_" + str(settings['MinGram']) + "_Max_" + str(settings['MaxGram']) + "__predict_piotrowski"

# for settings['UseNonHYDCDEvidence'] in [True, False]:
dyndict, dynastywordlist, bookwordlist = defaultdict(int), defaultdict(list), defaultdict(list)

historystart = min(hydcd_dynasties, key=lambda x: x[1])[1]
historyend = max(hydcd_dynasties, key=lambda x: x[2])[2]
# make a list of century slices of our valid dynasties
allcenturies = century_dict(historystart, historyend)
logging.info('We have %s dynasties (%s–%s) used in the 漢語大詞典 citations.' % (len(hydcd_dynasties), historystart, historyend))
# prepare the data frame
hydcd_profile = pd.DataFrame.from_dict(allcenturies, orient='index', columns=['count']).rename(columns={0:'century'})
hydcd_profile['century'] = hydcd_profile.index
hydcd_profile['dynasty'], hydcd_profile['dynstart'], hydcd_profile['dynend'] = zip(*hydcd_profile['century'].map(dynasty_handler))
for wordlength in range(1,18):
	hydcd_profile['X' + str(wordlength)] = 0.0

###########################################################
# get neologism information
###########################################################
#			    0			1	 2		   3		   4		 5		6
conn, cursor = database_connect()

sql = select_builder(None, settings)
logging.info('Query: ' + sql)
logging.info('Loading dictionary entries...')
cursor.execute(sql)
word_sources = list(starmap(HYDCDWord, cursor.fetchall()))
logging.info(str(cursor.rowcount) + ' dictionary entries with citation and year were loaded from the database.')

############################################################
# This is where the magic happens
###########################################################

hydcd_profile, dynastywordlist, bookwordlist, counter = profile_worker(word_sources, settings, None)

# do some calculations:
FlatEstimatedYear = int(counter['AverageSum'] / counter['words'])

logging.info("Processed " + str(counter['words']) + " words, " + str(counter['estimate']) + " based on estimations.")
logging.info("The dictionary's average word creation year is calculated as " + str(FlatEstimatedYear) + ".")
logging.info("The newest 漢語大詞典 word was found to be " + word_sources[0].cleanword + ", reported to be used in 《" + word_sources[0].book + "》 published " + word_sources[0].estimate + str(word_sources[0].meanyear) + ".\n")

############################################################
# prepare and print some statistics
###########################################################

# Add up the last 16 columns to sum all polysyllabic
hydcd_profile = hydcd_profile.drop('typelist',1)
hydcd_profile['poly'] = hydcd_profile.iloc[:,(settings['MinGram']+5):].sum(axis=1) # use one column less
if settings['MinGram'] == 1:
	hydcd_profile['weight'] = hydcd_profile['count'].sum() / hydcd_profile.shape[0] / hydcd_profile['count']
else:
	hydcd_profile['weight'] = hydcd_profile['poly'].sum() / hydcd_profile.shape[0] / hydcd_profile['poly']
hydcd_profile['weight'] = hydcd_profile['weight'].replace(np.inf, 1)
print(hydcd_profile.head())

hydcd_profile.to_csv(filenamer + ".csv", index=True)
logging.info("🐍 updated " + filenamer + ".csv")

logging.info('Analyzed %s entries in %.2f seconds.' % (counter['words'], (time.time() - start_time)))

cursor.close()
conn.close()
