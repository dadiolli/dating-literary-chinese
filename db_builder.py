# -*- coding: utf-8 -*-
"""
Build the diachronic database from the plain text dictionary.
Confer readme.md for step by step documentation.
Comment/uncomment lines in order to run/rerun specific steps
"""
import logging, time
global_start_time = time.time()
from modules.initialize_logger3 import *
initialize_logger('db_creation.log')
# import db_builder.db_hydcdtodb
# import db_builder.db_createwordpronunciation
import db_builder.db_gathersources
import db_builder.db_checkcbdb
import db_builder.db_manualsources
import db_builder.db_wordlist
import db_builder.db_trainer3
# import hydcd_profiler3

logging.info('⏱  Built DB in %.2f minutes.' % ((time.time() - global_start_time) / 60))