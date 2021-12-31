# Models
This is the models folder. Chronon models or co-dating models are be generated using one of the below scripts:
1. `hydcd2model.py` Create a chronon model from the *HYDCD* chronon pseudo-corpus
2. `grams2model.py` Create a chronon model from [CrossAsia n-gram datasets](https://crossasia.org/service/crossasia-lab/crossasia-n-gram-service/)
3. `grams2codatmodel.py` Create a document level (document co-dating) model from CrossAsia n-gram datasets

## Command line options:
* -w use only lexicalized character combinations
* -n create a full n-gram model 
* -t calculate *tf-idf*
* -e calculate *Temporal Entropy* (TE) 

# Using language models
* `catchron_corpus.py` is used to assign timestamps to a corpus of texts. Settings should match the settings used when training the model, cf. `readme.md` in the parent directory.
* `textimator.py` assigns a timestamp to a single plain text file – language models can be used optionally 

# Relevant settings
* `MinGram`: The minimum number of characters in considered words (e. g. 1 or 2)
* `MaxGram`: The maximum number of characters in considered words (e. g. 3 or 4)
* `HYDCDStandardize`: Normalize characters in the source text to default variants as given in the *HYDCD*, e. g. 為 will be converted to 爲. This can improve lexeme recognition recall.
* `ChrononMethods`: List of statistical methods considered. Leave empty (\[\]) to run lexicographical method(s) only. Available methods are:
	* 'cossim' = Cosine similarity,
	* 'tfidf' = Term frequency inverse document frequency weighted Cosine similarity,
	* 'jacsim' = Jaccard similarity,
	* 'kld' = Kullback Leibler Divergence (KLD)
	* 'kld_te' = Temporal Entropy weighted KLD,
	* 'nllr' = Normalized Log Likelihood Ratio (NLLR),
	* 'nllr_te' = Temporal Entropy weighted NLLR,
	* 'rand' = Select a random chronon / used as baseline
KLD and NLLR will yield identical results.
* `ChrononModel`: Statistical language model type, defaults to 'words'. If a suitable model is generated, 'grams' can be used instead. This requires much more computing power, memory and is time consuming.
* `ChrononPath`: Path to a statistical language model in `models` folder. Included model `chronons_allquotes_12_time` was generated from the *HYDCD* quotations
* `UseCBDB`: Accept names listed in `CBDB` as types for word models. Can be useful e.g. when names of contemporaries are mentioned in training and dating texts
* `UseCBDBPlaces`: Accept place names listed in `CBDB` as types for word models. This is discouraged, as place names tend to have very low temporal entropy.
* `UseTimeExpr`: Defaults to `True`. Decides if you want to consider temporal expressions in the input text. 
