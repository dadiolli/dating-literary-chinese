import sys, time

# make some preparations
from progress.bar import ShadyBar
from modules.toolbox3 import database_connect
from modules.initialize_logger3 import *
import pandas as pd
if __name__ == "__main__":
	initialize_logger("db_creation.log")

########################################################
# Load the source data
########################################################
manualsources = pd.read_csv('./modules/tbl_manualsources.csv')
manualsources = manualsources.where(pd.notnull(manualsources), None)

########################################################
# Make updates on `the_books`
########################################################

conn, cursor = database_connect()
logging.info('🐍  Manual source data is being added to `the_books`')
rows = 0
bar = ShadyBar('⏳  Working.', max=len(manualsources), width=60)
for ix, source in manualsources.iterrows():
	bar.next()
	cursor.execute("update `the_books` set title_py = %s, title_western = %s, startyear = %s, \
		endyear = %s, dynasty = %s, estimate = %s, source = %s, author = %s where clearbook = %s \
		", (source.title_py, source.title_western, source.startyear, \
		source.endyear, source.dynasty, source.estimate, source.source, source.author, source.clearbook))
	affected_rows = cursor.rowcount
	if affected_rows == 0:
		logging.info("❎ %s: 0 rows updated." % (source.clearbook))
	else:
		logging.info("✅ %s: %s rows updated." % (source.clearbook, affected_rows))
	rows += affected_rows
	conn.commit()	
bar.finish()
logging.info('🐍 %s book entries describing %s individual sources where updated. ' % (rows, len(manualsources)))
cursor.close()
conn.close()