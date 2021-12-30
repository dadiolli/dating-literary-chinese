import logging
import os.path
# inspired by 
# https://aykutakin.wordpress.com/2013/08/06/logging-to-console-and-file-in-python/
# Logging to Console and File In Python, 2017-12-27

def initialize_logger(outfile, loglevel = logging.INFO, logpath="logs"):
	logging.basicConfig(filename=os.path.join(os.getcwd(), logpath, outfile), format='%(asctime)s %(levelname)s %(message)s', level=loglevel)
	logger = logging.getLogger()

	handler = logging.StreamHandler()
	handler.setLevel(logging.DEBUG)
	formatter = logging.Formatter("%(message)s")
	handler.setFormatter(formatter)
	logger.addHandler(handler)