"Run (lexicographic) time depth estimation on a single .txt file"

###########################################################
# Import external modules
###########################################################

import argparse, matplotlib.pyplot as plt, pandas as pd, sys, datetime

###########################################################
# Import own modules
###########################################################

from modules.classes3 import ResearchText
from modules.dynasties3 import dynasty_handler
from modules.neologism_profiler import neologism_profiler_grams, profile_dater
from modules.projector3 import Projector
from modules.settings3 import settingprinter, settings_single as settings
from modules.visualizations import export_barplot
from modules.initialize_logger3 import *

###########################################################
# Grab command line arguments
###########################################################

parser = argparse.ArgumentParser(description='Pass the text to be analyzed.')
parser.add_argument('filename', metavar='File name', type=str, nargs='?', help='🐍 Please enter the name of the file you want to analyze.')
parser.add_argument('mode', metavar='Running mode', type=int, nargs='?', default=1, help='🐍 Select desired running mode, (1) default, (2) demo.')
args = parser.parse_args()

###########################################################
# Initialize
###########################################################

initialize_logger("textimator3.log")

print(settings['WordFreqListLength'])
usewords = 'words_' if settings['WordFreqListLength'] else ''
split = '_fullsplit_' + str(settings['Split']) if settings['Split'] else ''
observationfile = 'results/textimator_observations_' + usewords + 'exclude_' + str(settings['ExcludeSelf']).lower() + '_punctuation_' + str(settings['Punctuation']).lower() + '_NonHYDCD_' + str(settings['UseNonHYDCDEvidence']).lower() + split + '.csv'

file_exists = os.path.isfile(observationfile)
if not file_exists:
	logging.info("🐼 Creating file %s to store observations." % (observationfile))
	observation_base = pd.read_csv('results/zhengshi_resultbase.csv', index_col=['filename', 'part'])
	observation_base.to_csv(observationfile, encoding='utf-8', index=True)
else:
	logging.info("🐼 Observation file %s already exists. Will extend or overwrite as necessary." % (observationfile))
observations = pd.read_csv(observationfile, index_col=['filename', 'part'])

if not args.filename:
	args.filename = input("🐍 Please enter the name of the file you want to analyze and hit Enter: ")
file = open("primary_sources/" + args.filename)
logging.info("📕 " + file.name + " is analyzed.")

settingprinter(settings)
# if args.mode != 2: start_time = time.time()
text = ResearchText(file, settings['Punctuation'], settings['Split'], tradify=True) # standardize is True by default
if settings['Split']:
	if len(text.original) <= settings['Split']:
		settings['Split'] = False
		text = ResearchText(file, settings['Punctuation'])
		logging.info('Input text is too short. Splitting was deactivated.')

current_part = 0
loop = 1 if settings['Split'] == False else len(text.text) - 1	

###########################################################
# Loop through parts of the input text
###########################################################

while current_part < loop: # through parts and skip last
	dynastywordlist, bookwordlist, observations, profile = neologism_profiler_grams(text, settings, current_part=0, observations=observations)
	
	###########################################################
	# do inloop calculations:
	###########################################################

	observations.to_csv(observationfile, encoding='utf-8', index=True) 
	current_part += 1 # internal loop
	logging.info(observationfile + " was updated with the results.")

	if settings['ListOutput']:
		for b in bookwordlist:
			print(b)

###########################################################
# Display results
###########################################################

# observation_header = str(settings['FreqListLength']) + '-' + str(settings['MinGram']) + '-'
	# projections = Projector(observations.loc[text.filename, observation_header + 'flat'].mean(), settings)
logging.info("Profile dating results: %.0f–%.0f. [Expected types in text creation century: %2.f.]" % (observations.loc[text.filename, 'plainsimplechron'].mean(), observations.loc[text.filename, 'plainsimplechron'].mean()+100, observations.loc[text.filename, 'plaintargetline'].mean()))
logging.info("\t using linear weight correction: %.0f–%.0f. [Expected types: %.2f]" % (observations.loc[text.filename, 'simplechron'].mean(), observations.loc[text.filename, 'simplechron'].mean()+100, observations.loc[text.filename, 'smoothedtargetline'].mean()))
logging.info("\t using s-shaped weight correction: %.0f–%.0f. [Expected types: %.2f]" % (observations.loc[text.filename, 'piotsimplechron'].mean(), observations.loc[text.filename, 'piotsimplechron'].mean()+100, observations.loc[text.filename, 'piotrowskitargetline'].mean()))

if settings['UseCBDB']:
	logging.info("\t using linear weight correction and names: %.0f–%.0f." % (observations.loc[text.filename, 'simplechrononer'].mean(), observations.loc[text.filename, 'simplechrononer'].mean()+100))
	if settings['UseTimeExpr']: logging.info("\t using linear weight correction, names and temporal expressions: %.0f–%.0f." % (observations.loc[text.filename, 'combochronon'].mean(), observations.loc[text.filename, 'combochronon'].mean()+100))

if settings['UseTimeExpr']:
	try:
		logging.info("Newest date in text dating results: %.0f–%.0f." % (observations.loc[text.filename, 'ndt_dated'].mean(), observations.loc[text.filename, 'ndt_dated'].mean()+100))
	except:
		logging.info("Newest date in text dating results: insufficient data.")

try:
	projections = Projector(observations.loc[text.filename, 'ayl_w_' + str(settings['WordFreqListLength'][0])].mean(), settings)
	logging.info("Average Year of Lexicalization (AYL) of the text's lexeme types is %s." % (observations.loc[text.filename, 'ayl_w_' + str(settings['WordFreqListLength'][0])].mean()))
	logging.info("Using AYL, the text's creation is projected to %s. This is highly experimental and dates the text to the %s (%s)" % (projections.linear, projections.centstring, dynasty_handler(projections.linear).name))
except:
	logging.info("Currently no suitable data / format or settings for AYL projector.")

if settings['StatisticsOutput']:
	profile.to_csv('results/' + datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S") + '_textimator_' + text.filename + '.csv')
	export_barplot(profile, 'smoothed', "Word types (linear-smoothed)", observations.loc[(text.filename, 0)], title=text.filename, exportpath='results/')
	# export_barplot(profile, 'smoothed', "Words (smoothed)", text.filename + observation_header + str(settings['MaxGram']))

