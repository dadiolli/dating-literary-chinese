import matplotlib.pyplot as plt, numpy as np, os, pandas as pd, regex as re
import matplotlib.font_manager as mfm

# define standard font
plt.rcParams["font.family"] = "Open Sans"
# chinesefont = mfm.FontProperties(fname="/Users/Tilman/Library/Fonts/SourceHanSansTC-Regular.otf")
# avoid Type3 conversion, use TrueType instead for the PDF
chinesefont = mfm.FontProperties(fname="/Library/Fonts/Microsoft/SimHei.ttf")
chinesefont.set_size(24)

import os
os.environ['NUMEXPR_MAX_THREADS'] = '11'

def export_barplot(data, ycolumn, ycolumntitle, observation=None, title='', exportpath=''):
	# original color schneme is color=['#dd1111', '#8f0d0d', '#1b7ade']
	colors = {'smoothed': '#a8a8a8', 
			  'count': '#dedede',
			  'piotrowskismoothed': '#53687e', 
			  'names': '#235789', 
			  'places': '#1b7ade',
			  'times': '#3c1676'
			  }
	barstacks = [ycolumn]
	if 'names' in data: barstacks.append('names')
	if 'places' in data: barstacks.append('places')
	if 'times' in data: barstacks.append('times')
	barcolors = [colors[x] for x in barstacks]
	
	myplot = data.plot(kind='bar', stacked=True, x='century',y=barstacks, figsize = (14,10), width=0.8, color=barcolors)
	
	if isinstance(observation, pd.Series):
		
		# put an arrow on the known row 
		# predicted = observation.simplechrononer
		try:
			predicted = {'smoothed': observation.simplechrononer, # observation.simplechron, # 
						 'count': observation.plainsimplechron,
						 'piotrowskismoothed': observation.piotsimplechron
						}

			targetline = {'smoothed': observation.smoothedtargetline,
						  'count': observation.plaintargetline,
						  'piotrowskismoothed': observation.piotrowskitargetline
						 }
		except:
			print("📊 Plotting temporal profile… No prediction data available.")
		
		try:
			hit = {'smoothed': observation.simplechronerhit, # simplechronhit
				   'count': observation.plainsimplechronhit,
				   'piotrowskismoothed': observation.piotsimplechronhit
			}
		except:
			print("📊 Plotting temporal profile… insufficient metadata for evaluating the prediction.")

		try: #this is if we have "known" data
			known = observation.known_century
			known_arrow_ypos = int(data.totals[observation.known_century] + int(data.totals.max() / 69))
			known_text_ypos= int(data.totals[observation.known_century] + int(data.totals.max() / 7))
			arrowcolor = 'black'

			row_to_highlight = data.index.get_loc(predicted[ycolumn])
			myplot.get_children()[row_to_highlight].set_color('#dd1111') # mark predicted row
			
			row_to_highlight = data.index.get_loc(known)
			myplot.get_children()[row_to_highlight].set_color('#000000') # black for known row

			if known == predicted[ycolumn]:
				arrowcolor = '#00882b'
				myplot.get_children()[row_to_highlight].set_color('#00882b') # green for correct prediction

			plt.annotate('published ' + str(int(observation.known_year)), xy=(data.index.get_loc(known), known_arrow_ypos), xytext=(data.index.get_loc(known), known_text_ypos),
				va="top", ha="center", arrowprops=dict(facecolor=arrowcolor, shrink=0.05, edgecolor=arrowcolor))

			full_title = '%s_%s_%s_%s_%s_%s' % (observation.name, observation.known_century, int(observation.known_year), predicted[ycolumn], hit[ycolumn], observation.title.replace('/','-'))
		except: # just plot the prediction
			print("📊 Plotting temporal profile… insufficient metadata for title. Using filename instead.")
			try:
				row_to_highlight = data.index.get_loc(predicted[ycolumn])
				myplot.get_children()[row_to_highlight].set_color('#000000') # mark predicted row
				try:
					cleaned_title = re.sub('\p{IsHan}', '', observation.title)
				except:
					cleaned_title = re.sub('\p{IsHan}', '', title)
				full_title = '%s_%s' % (cleaned_title, observation.simplechron)
			except:
				print("📊 Plotting… having trouble naming the plot.")
				cleaned_title = re.sub('\p{IsHan}', '', title)
				full_title = '%s' % (cleaned_title)

	plt.xlabel("Centuries"); plt.ylabel(ycolumntitle); plt.title(title, size="x-large")
	labels = list(data.centurylabel)
	plt.xticks(np.arange(len(labels)), labels, rotation=90)
	try:
		plt.text(30, data.smoothed.max() * 0.85, observation.title, fontproperties=chinesefont, ha='right', wrap=False) 
		plt.axhline(y=targetline[ycolumn], color='#888888')
	except:
		pass
	plt.savefig(exportpath + full_title + ".pdf", format="pdf")
	plt.close()

