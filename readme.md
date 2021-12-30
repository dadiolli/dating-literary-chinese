# Playing around
A *GUI* version that includes the main literary Chinese textual dating features of the scripts here is available online at [https://www.visualtime.schalmey.de/upload](https://www.visualtime.schalmey.de/upload). This uses default settings.

# (Basic) usage in Terminal / console
* Run `textimator.py filename.txt` for any plain text file in `primary_sources`
* The diachronic lexeme database is required for most purposes, see [Setting up the database](#dbsetup)

## Settings{#settings}
* `textimator.py` uses the settings given in `settings_single` in `modules.settings3`. These settings can be modified when necessary. 
	* `MinGram`: The minimum number of characters in considered words (e. g. 1 or 2)
	* `MaxGram`: The maximum number of characters in considered words (e. g. 3 or 4)
	* `UseDFZTraining`: Consider extra training data from the [CrossAsia N-gram dataset of Chinese local gazetteers (中國地方誌)](https://zenodo.org/record/2634846).
	* `UseNonHYDCDEvidence`: Consider extra training data from *zhengshi* 正史 and *Loewe* corpora
	* `HYDCDStandardize`: Normalize characters in the source text to default variants as given in the *HYDCD*, e. g. 為 will be converted to 爲. This can improve lexeme recognition recall.
	* `WordFreqListLength`: List of word list lengths for calculation of *Average Year of Lexicalization* (*AYL*). Defaults to \[1\]. Values between 0.01 and 1 will cause a relative amount of the most commonly appearing lexemes of the input text to be used, e. g. 0.05 means 5 %, 1 means 100 %. Values greater than 1 will be interpreted as an absolute number, e. g. 1000 will consider the 1.000 most common lexemes and so on.
	* `ChrononMethods`: List of statistical methods considered. Leave empty (\[\]) to run lexicographical method(s) only. Available methods are:
		* 'cossim' = Cosine similarity,
		* 'tfidf' = Term frequency inverse document frequency weighted Cosine similarity,
		* 'jacsim' = Jaccard similarity,
		* 'kld' = Kullback Leibler Divergence (KLD)
		* 'kld_te' = Temporal Entropy weighted KLD,
		* 'nllr' = Normalized Log Likelihood Ratio (NLLR),
		* 'nllr_te' = Temporal Entropy weighted NLLR,
		* 'rand' = Select a random chronon / used as baseline
	* KLD and NLLR will yield identical results
	* `ChrononModel`: Statistical language model type, defaults to 'words'. If a suitable model is generated, 'grams' can be used instead. This requires much more computing power, memory and is time consuming.
	* `ChrononPath`: Path to a statistical language model in `hydcd` folder. Included model `chronons_allquotes_12_time` was generated from the *HYDCD* quotations
	* `UseTimeExpr`: Defaults to `True`. Decides if you want to consider temporal expressions in the input text.

# Setting up the database {#dbsetup}
* A MariaDB / mySQL database is required
* The DB connection needs to be configured in `config` in `modules/toolbox3.py`
* Creating the database from scratch requires an UTF-8 plain text version of Hanyu da cidian (HYDCD) 漢語大辭典 / follow the steps described in [Creating a diachronic lexeme database based on the HYDCD from scratch](#dbfromscratch) to do so. 
* Instead, a stripped down, minimal version can be imported from SQL dumps in `sql`:
	* `dynasties.sql`
	* `the_books.sql`
	* `the_words.sql`
	* `the_citations.sql` (not required)
* For some purposes, we will also need some contents from [China Biographical Database (CBDB)](https://projects.iq.harvard.edu/cbdb/home). The Latest CBDB can be obtained from [CBDBs GitHub](https://github.com/cbdb-project/cbdb_sqlite/blob/master/latest.7z).
	* However, the data is provided in SQLite format. It can be converted using a *Perl* script, `sql/cbdb/sqliteconvert.pl`.
	* Or you can use the prepared files from the 2016 version of CBDB. Those can be found in sql/cbdb/mysql-{tablename}.sql or cbdb_mysql_minimal.sql
	* The following tables should be present:
		* `addresses`
		* `altname_data`
		* `altname_codes`
		* `text_data`
		* `text_codes`
		* `biog_main`
			
# Other Python scripts 
## Creation of statistical language models 
* Three very similar scripts create statistical language models:
	1. `hydcd2model.py` Create a chronon model from the *HYDCD* chronon pseudo-corpus
	2. `grams2model.py` Create a chronon model from [CrossAsia n-gram datasets](https://crossasia.org/service/crossasia-lab/crossasia-n-gram-service/)
	3. `grams2codatmodel.py` Create a document level (document co-dating) model from CrossAsia n-gram datasets
* Command line options:
	* -w use only lexicalized character combinations
	* -n create a full n-gram model 
	* -t calculate *tf-idf*
	* -e calculate *Temporal Entropy* (TE) 

## Using language models
* `catchron_corpus.py` is used to assign timestamps to a corpus of texts. [Settings](#settings) should match the settings used when training the model.

## Training and using lexicographic methods
* `corpusgrams_textimator.py` generates temporal statistics based on the diachronic lexicalization observed in a given input corpus text selection.
* After running with training data, statistical calculations with the results are used for the `profile_dater` function in `modules.neologism_profiler`. These depend again on the given n-gram space (1–3, 1–2, 2–3, 2–4 character words) as does the *HYDCD* bias that can be utilized for century weight correction. 
	
# Creating a diachronic lexeme database based on the *HYDCD* from scratch {#dbfromscratch}

* db_builder.py
	* This will run all scripts in the required order – this will take around 16–30 minutes depending on hardware resources
	* We assume that the plain text *HYDCD* is available in `hydcd/hanyudacidian.txt` and the DB is set up with required CBDB tables as listed above in *Setting up the database*

## Read the dictionary, prepare preliminary tables and fill them

* db_hydcdtodb.py
	* character / main entries (marked with an asterisk \*) are written to the hydcd_entries table
	* an inner loop will write the word entries / subentries and their glosses to the hydcd_words table.

## Add pinyin 拼音 / zhuyin 注音

* db_createwordpronunciation
	* creates pinyin and zhuyin pronunciation for poly-syllabic entries. Based on the pronunciation given for the characters in the mono-syllabic entries.

## Collecting meta data and creating the main tables

* db_gathersources
	* requires the dynasty model and adds hydcd_dynasties table if unavailable
	* reads the attestations / quotes and generates
		* the_words – list of all words with attestations, includes first / earliest attestations
		* the_books - list of all distinguishable sources of attestations
		* the_citations - list of all attestations (n:m). Can be used for creation of an auxiliary corpus.

* db_checkcbdb
	* gather author biographical data and 
	* texts publication data 
	* and enrich the_books table where applicable

* db_manualsources
	* override HYDCD data with research from tbl_manualsources.csv
	* this is necessary especially for the earliest (and most often cited) sources

## Create auxiliary files

* db_wordlist
	* creates txt files of wordlists for quick access 
	* has two flavors, with and without punctuation
	* also outputs full list of hydcd entries (even if they have no citation / source data)

## Enhance the diachronic database

* db_trainer
	* will collect further evidence from the corpus
	* update / enhance attestations where applicable
* db_dfz_trainer
	* this is run separately from the main directory. The [CrossAsia N-gram dataset of Chinese local gazetteers (中國地方誌)](https://zenodo.org/record/2634846) needs to be in `primary_sources/difangzhi-grams`

## Create more auxiliary files

* hydcd_profiler
	* diachronic lexicalization as seen through the HYDCD is strongly biased. As this is more due to a preference for certain texts rather than cyclic creativity in the creation of new words, we should be able to correct the bias, so we 
	* generate a »profile« how many lexemes where added into the lexicon during each century
	* and we also want to create that kind of profile for the corpus-enhanced database

