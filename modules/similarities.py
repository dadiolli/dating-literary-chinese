"Methods to calculate distance / similarity between BoW models"

###########################################################
# Import Python modules
###########################################################

from collections import Counter
import math, numpy as np
dummyminifreq = 0.00000002 # 0.00000002 
# dummyminifreq = 0.00000006
# dummyminifreq = 0.000000015
beta, my = 0.01, 0.4


def jelinek_mercer(word, word_textfreq, word_corpfreq):
	"Apply Jelinek Mercer smoothing for unseen words."
	return (1 - beta) * word_textfreq + beta * word_corpfreq

def dirichlet(word, word_textfreq, word_corpfreq, totaltokens_query):
	return totaltokens_query / (totaltokens_query + my) * word_textfreq + my / (my + totaltokens_query) * word_corpfreq

def linear_interpolation(word, word_textfreq, word_corpfreq):
	"Apply linear interpolation / Jelinek mercer smoothing for unseen words."
	return beta * word_textfreq + (1 - beta) * word_corpfreq

def chronon_low(chronon_min):
	"Apply chronon low smoothing."
	# return 0.5 * chronon_min
	return dummyminifreq

# 0.00000002 # use for missing dimensions dfz 7–10
# need to validate!

class Similarities():
	"Use an object to call similarity metrics dynamically."
	def __init__(self, textfreq, chronfreq, corpfreq=False, entropy_dict=False, tfidf_dict=False, totaltokens=0, dummyfreq=False, idf_dict=False, model_type='chronon'):
		self.textfreq, self.chronfreq = textfreq, chronfreq
		self.corpfreq = corpfreq
		self.entropy_dict = entropy_dict
		self.tfidf_dict = tfidf_dict
		self.idf_dict = idf_dict
		self.totaltokens = totaltokens
		self.chronon_minfreq = min(self.chronfreq.values())
		self.dummyfreq = dummyminifreq if dummyfreq == False else dummyfreq
		self.model_type = model_type
	
	def jacsim(self):
		"Compute Jaccard similarity of two vectors."
		common = len(set(set(self.textfreq.keys()) & set(self.chronfreq.keys())))
		return (float(common) / (len(self.textfreq) + len(self.chronfreq) - common))

	def cossim(self): #https://stackoverflow.com/questions/22381939/python-calculate-cosine-similarity-of-two-dicts-faster
		"Compute Cosine similarity of two vectors."
		up = 0.0
		for key in (set(self.textfreq.keys()) & set(self.chronfreq.keys())):
			up += self.textfreq[key] * self.chronfreq[key]
		if up == 0:
			return 0
		return up / (np.sqrt(np.dot(list(self.textfreq.values()), list(self.textfreq.values()))) * np.sqrt(np.dot(list(self.chronfreq.values()), list(self.chronfreq.values()))))

	def tfidf(self): 
		"Compute Cosine similarity of two vectors, TF-IDF weighted."
		# with aggregated models, proved better to compare idf weighted chronon freqs to unweighted text freqs
		if self.model_type == 'chronon':
			up = 0.0
			text_tfidfdict, corpus_tfidfdict = dict(), dict()
			for key in (set(self.textfreq.keys()) & set(self.tfidf_dict.keys())):
				up += self.textfreq[key] * self.tfidf_dict[key]
			if up == 0:
				return 0
			return up / (np.sqrt(np.dot(list(self.textfreq.values()), list(self.textfreq.values()))) * np.sqrt(np.dot(list(self.tfidf_dict.values()), list(self.tfidf_dict.values()))))
		else:	
			# "Compute Cosine similarity of two vectors, TF-IDF weighted, for document level models"
			# with document models, tf-idf will only work when idf weighted chronon freqs are compared to idf weighted text freqs
			up = 0.0
			text_tfidfdict, corpus_tfidfdict = dict(), dict()
			for key in (set(self.textfreq.keys()) & set(self.tfidf_dict.keys())):
				text_tfidfdict[key] = self.textfreq[key] * self.idf_dict[key]
				up += text_tfidfdict[key] * self.tfidf_dict[key]
			if up == 0:
				return 0
			return up / (np.sqrt(np.dot(list(text_tfidfdict.values()), list(text_tfidfdict.values()))) * np.sqrt(np.dot(list(self.tfidf_dict.values()), list(self.tfidf_dict.values()))))
			

	# def nllr(self, entropy_dict=False):
	# 	"Will calculate Normalized Log Likelihood Ratio."
	# 	nllr, counter = 0.0, Counter()
		# if entropy_dict:
		# 	for word in self.textfreq:
		# 		if word in self.chronfreq and self.corpfreq[word] > 0:
		# 			nllr += get_entropy(word, entropy_dict) * jelinek_mercer(word, self.textfreq[word], self.corpfreq[word]) * np.log2(self.chronfreq[word] / self.corpfreq[word])
		# 		if word not in self.chronfreq and word in self.corpfreq and self.corpfreq[word] > 0:
		# 			nllr += get_entropy(word, entropy_dict) * jelinek_mercer(word, self.textfreq[word], self.corpfreq[word]) * np.log2(jelinek_mercer(word, 0, self.corpfreq[word]) / self.corpfreq[word])
		# else:
		# 	for word in self.textfreq:
		# 		if word in self.chronfreq and self.corpfreq[word] > 0:
		# 			nllr += 1 * jelinek_mercer(word, self.textfreq[word], self.corpfreq[word]) * np.log2(self.chronfreq[word] / self.corpfreq[word])
		# 		if word not in self.chronfreq and word in self.corpfreq and self.corpfreq[word] > 0:
		# 			nllr += 1 * jelinek_mercer(word, self.textfreq[word], self.corpfreq[word]) * np.log2(jelinek_mercer(word, 0, self.corpfreq[word]) / self.corpfreq[word])
		# return nllr	
		
		# dirichlet(word, self.textfreq[word], self.corpfreq[word], self.totaltokens)

	def nllr(self, entropy_dict=False):
		"Will calculate Normalized Log Likelihood Ratio."
		nllr, counter = 0.0, Counter()
		if entropy_dict:
			for word in self.textfreq:
				if word in self.chronfreq and self.corpfreq[word] > 0:
					nllr += get_entropy(word, entropy_dict) * self.textfreq[word] * np.log2(self.chronfreq[word] / self.corpfreq[word])
					# counter['total'] += 1
					# counter['chron_has_word'] += 1
				if word not in self.chronfreq and word in self.corpfreq and self.corpfreq[word] > 0:
					# nllr += get_entropy(word, entropy_dict) * self.textfreq[word] * np.log2(dummyminifreq / self.corpfreq[word])
					# nllr += get_entropy(word, entropy_dict) * self.textfreq[word] * np.log2(jelinek_mercer(word, self.textfreq[word], self.corpfreq[word]) / self.corpfreq[word])
					nllr += get_entropy(word, entropy_dict) * self.textfreq[word] * np.log2(self.dummyfreq / self.corpfreq[word])
		# 		counter['total'] += 1
		# 		counter['chron_not_word'] += 1
		# print("Anteil Wort aus chronon-Modell %.2f %%, dummy freq %.2f %%, gesamt %s types." % (counter['chron_has_word'] / counter['total'], counter['chron_not_word'] / counter['total'], counter['total']))
		else:
			for word in self.textfreq:
				if word in self.chronfreq and self.corpfreq[word] > 0:
					nllr += 1 * self.textfreq[word] * np.log2(self.chronfreq[word] / self.corpfreq[word])
				if word not in self.chronfreq and word in self.corpfreq and self.corpfreq[word] > 0:
					nllr += 1 * self.textfreq[word] * np.log2(self.dummyfreq / self.corpfreq[word])
		return nllr	

	def nllr_te(self):
		"Compute Normalized Log Likelihood Ratio, Temporal entropy weighted"
		return self.nllr(entropy_dict=self.entropy_dict)

	def kld(self, entropy_dict=False):
		"Compute Kullback-Leibler divergence"
		kld = 0.0
		for word in self.textfreq:
			if word in self.chronfreq:
				kld += get_entropy(word, entropy_dict) * self.textfreq[word] * np.log2(self.textfreq[word] / self.chronfreq[word])
			elif entropy_dict and word in entropy_dict:
				kld += get_entropy(word, entropy_dict) * self.textfreq[word] * np.log2(self.textfreq[word] / self.dummyfreq)
			else:
				kld += 1 * self.textfreq[word] * np.log2(self.textfreq[word] / self.dummyfreq)
		return kld

	def kld_te(self):
		"Compute Kullback-Leibler divergence, Temporal entropy weighted"
		return self.kld(entropy_dict=self.entropy_dict)

	def rand(self):
		"Will randomize elsewhere, this is not the place."
		return 0

###########################################################
# Cosine similarity
###########################################################

def cossim(v1, v2): #https://stackoverflow.com/questions/22381939/python-calculate-cosine-similarity-of-two-dicts-faster
	# v2 is the chronons freq dict
	# adding missing values has no effect
	up = 0.0
	for key in (set(v1.keys()) & set(v2.keys())):
		v1_value = v1[key]
		v2_value = v2[key]
		up += v1_value * v2_value
	if up == 0:
		return 0
	return up / (np.sqrt(np.dot(list(v1.values()), list(v1.values()))) * np.sqrt(np.dot(list(v2.values()), list(v2.values()))))	

###########################################################
# Jaccard similarity
###########################################################

def jacsim(v1,v2):
	# Anzahl der types, die in beiden Gruppen vorkommen geteilt durch Gesamtzahl der types beider Gruppen!
	# Die Schnittmenge wird also im Nenner von den Längen beider dicts abgezogen
	total = len(set(set(v1.keys()) & set(v2.keys()))) 
	return(float(total) / (len(v1) + len(v2) - total)) 

###########################################################
# Temporal entropy
###########################################################

def get_entropy(word, entropy_dict):
	"Without entropy, return 1, no weighting, otherwise get weight from dict"
	if entropy_dict is False:
		return 1
	else:
		return entropy_dict[word]

###########################################################
# Kullback-Leibler divergence
###########################################################

def kld(textfreq, chronfreq, entropy_dict=False):
	kld = 0.0
	for word in textfreq:
		if word in chronfreq:
			kld += get_entropy(word, entropy_dict) * textfreq[word] * np.log2(textfreq[word] / chronfreq[word])
		elif entropy_dict and word in entropy_dict:
			kld += get_entropy(word, entropy_dict) * textfreq[word] * np.log2(textfreq[word] / dummyminifreq)
		else:
			kld += 1 * textfreq[word] * np.log2(textfreq[word] / dummyminifreq)
	return kld

###########################################################
# Normalized Log-likelihood ratio
###########################################################

def nllr(textfreq, chronfreq, corpfreq, entropy_dict=False):
	"Will calculate Normalized Log Likelihood Ratio"
	nllr = 0.0
	for word in textfreq:
		if word in chronfreq:
			if corpfreq[word] > 0: # can be zero on low precision
				nllr += get_entropy(word, entropy_dict) * textfreq[word] * np.log2(chronfreq[word] / corpfreq[word])
			else:
				nllr += get_entropy(word, entropy_dict) * textfreq[word] * np.log2(chronfreq[word] / dummyminifreq)
		if word not in chronfreq and word in corpfreq:
			if corpfreq[word] > 0: # can be zero on low precision
				nllr += get_entropy(word, entropy_dict) * textfreq[word] * np.log2(dummyminifreq / corpfreq[word])
			else:
				nllr += get_entropy(word, entropy_dict) * textfreq[word] * np.log2(dummyminifreq / dummyminifreq)
	return nllr


def nllr_tfidf(textfreq, chronfreq, corpfreq, tfidf):
	"Will calculate Normalized Log Likelihood Ratio"
	nllr = 0.0
	for word in textfreq:
		if word in chronfreq:
			if corpfreq[word] <= 0: # can be zero on low precision
				nllr += tfidf[word] * textfreq[word] * np.log(chronfreq[word] / dummyminifreq)
			else:
				nllr += tfidf[word] * textfreq[word] * np.log(chronfreq[word] / corpfreq[word])
	return nllr
