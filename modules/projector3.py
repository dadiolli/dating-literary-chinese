import math

class Projector():
	def __init__(self, flatyear, settings):

		self.linear = self.projector(flatyear, settings)
		self.sigmoid = self.sigmoid_projector(flatyear, settings)
		if self.linear is False:
			self.centring = "No suitable regression available for given settings."
		else:	
			self.century = int(self.linear / 100)
			if self.century >= 0:
				self.era = "A.D."
				self.century += 1
			else:
				self.era = "B.C."

			self.centstring = str(abs(self.century)) + " century " + self.era

	def projector(self, flatyear, settings):
		"Projects the estimated year using Loewe + 正史 corpus observations"
		if 'WordFreqListLength' in settings:
			if settings['MinGram'] == 2 and settings['MaxGram'] == 4 and settings['WordFreqListLength'][0] == 0.9 and settings['UseNonHYDCDEvidence'] == False:
				slope, intercept = 2.57, 78.6
			
			elif settings['MinGram'] == 2 and settings['MaxGram'] == 4 and settings['WordFreqListLength'][0] == 0.9 and settings['UseNonHYDCDEvidence'] == True:
				slope, intercept = 2.4139, 904.0291
		
			# # 
			# elif settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['MaxGram'] == 4 and settings['WordFreqListLength'][0] == 0.15 and settings['Split'] == False and settings['UseNonHYDCDEvidence'] == False:
			# 	slope = 4.2208
			# 	intercept = 639.8078
			# elif settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['MaxGram'] == 4 and settings['WordFreqListLength'][0] == 1 and settings['UseNonHYDCDEvidence'] == False::
			# 	slope = 4.5438
			# 	intercept = -202.9847
			# elif settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['MaxGram'] == 4 and settings['WordFreqListLength'][0] == 1 and settings['UseNonHYDCDEvidence'] == True and settings['UseDFZTraining']:				

	
		elif 'FreqListLength' in settings:	
			if settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['FreqListLength'] == 0.015 and settings['Split'] == False and settings['UseNonHYDCDEvidence'] == True:
				slope = 4.2654
				intercept = 2169.6354
			elif settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['FreqListLength'] == 0.05 and settings['Split'] == 100000 and settings['UseNonHYDCDEvidence'] == True:
				slope = 4.7764
				intercept = 2344.9882 
			elif settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['FreqListLength'] == 0.05 and settings['Split'] == False and settings['UseNonHYDCDEvidence'] == True:
				slope = 4.5023
				intercept = 1967.6634
			elif settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['FreqListLength'] == 40000 and settings['Split'] == False and settings['UseNonHYDCDEvidence'] == True:
				slope = 4.8097
				intercept = 2220.7436
			elif settings['Punctuation'] == True and settings['MinGram'] == 1 and settings['FreqListLength'] == 20000 and settings['Split'] == False and settings['UseNonHYDCDEvidence'] == False:
				slope = 9.7538
				intercept = 2846.3805
			elif settings['Punctuation'] == False and settings['MinGram'] == 2 and settings['FreqListLength'] == 100000:
				slope = 5.329
				intercept = 299.798
			elif settings['Punctuation'] == False and settings['MinGram'] == 2 and settings['FreqListLength'] == 0.01:
				slope = 4.2246
				intercept = 759.7554	
			elif settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['FreqListLength'] == 0.05:
				slope = 4.3414
				intercept = 508.8327
			elif settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['FreqListLength'] == 1:
				slope = 4.5438
				intercept = -202.9847
			elif settings['Punctuation'] == False and settings['MinGram'] == 1 and settings['FreqListLength'] == 5000:
				slope = 16.513
				intercept = 5641.566	
		
		if 'slope' not in locals():
			return False
			
		projected_year = slope * flatyear + intercept
		return int(projected_year)

	def sigmoid_projector(self, flatyear, settings):
		"Projects the estimated year using 正史 corpus observations and sigmoid function"
		if settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['FreqListLength'] == 0.015 and settings['Split'] == False and settings['UseNonHYDCDEvidence'] == True:
			scope = 2900
			slope = 4.2654
			intercept = 2169.6354
			exponent = 0.0077
			shift = 550
		elif settings['Punctuation'] == True and settings['MinGram'] == 2 and settings['FreqListLength'] == 40000 and settings['Split'] == False and settings['UseNonHYDCDEvidence'] == True:
			scope = 2900
			slope = 4.8097
			intercept = 2220.7436
			exponent = 0.0077
			shift = 550
		elif settings['Punctuation'] == True and settings['MinGram'] == 1 and settings['FreqListLength'] == 20000 and settings['Split'] == False and settings['UseNonHYDCDEvidence'] == False:
			scope = 3084
			slope = 9.7538
			intercept = 2846.3805
			exponent = 0.020
			shift = 350
		else:
			return 0
		projected_year = scope / (1 + slope * math.exp(-exponent * (flatyear + shift))) - intercept / math.exp(1)
		return int(projected_year)