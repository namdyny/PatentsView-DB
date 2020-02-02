# inserts new rawinventors into long persistent inventor disambig table
import sys
import os
import pandas as pd
from sqlalchemy import create_engine
from warnings import filterwarnings
import csv
import re, os, random, string, codecs
import sys
from collections import Counter, defaultdict
import time
import tqdm
project_home = os.environ['PACKAGE_HOME']
from Development.helpers import general_helpers

import configparser

config = configparser.ConfigParser()
config.read(project_home + '/Development/config.ini')

db_con = general_helpers.connect_to_db(config['DATABASE']['HOST'], config['DATABASE']['USERNAME'],
                                       config['DATABASE']['PASSWORD'], config['DATABASE']['NEW_DB'])

disambig_folder = "{}/disambig_output/".format(config['FOLDERS']['WORKING_FOLDER'])

old_db = config['DATABASE']['OLD_DB']
new_db = config['DATABASE']['NEW_DB']
new_db_timestamp = new_db.replace('patent_', '')

outfile_name = 'persistent_inventor_long_{0}.tsv'.format(new_db_timestamp)
outfile_fp = disambig_folder + outfile_name

############# 1. get column names of persistent_inventor_disambig_long table & create output file
result = db_con.execute("select column_name from information_schema.columns where table_schema = '{0}' and table_name = '{1}'".format(new_db, 'persistent_inventor_disambig_long'))
result_cols = [r[0] for r in result]
pid_long_cols = [x for x in result_cols if x != 'id']
print(pid_long_cols)

header = pid_long_cols
header_df = pd.DataFrame(columns = header)
header_df.to_csv(outfile_fp, index=False, header=True, sep='\t')


# get total rows in the rawinventor table
result = db_con.execute('select count(*) from {0}.{1}'.format(new_db,'rawinventor'))
total_rows = [r[0] for r in result][0]
total_rows

############# 2.output rawinventor rows from newdb
limit = 300000
offset = 0

start = time.time()
itr = 0

print('Estimated # of rounds: ', total_rows/300000)

while True:
    print('###########################################\n')
    print('Next iteration... ', itr)
    
    sql_stmt_template = "select uuid, inventor_id from {0}.{1} order by uuid limit {2} offset {3};".format(new_db, 'rawinventor', limit, offset)
    
    print(sql_stmt_template)
    result = db_con.execute(sql_stmt_template)
    
    # r = tuples of (uuid, inventor_id)
    chunk_results = [(r[0], new_db_timestamp, r[1]) for r in result]

    # means we have no more result batches to process! done
    if len(chunk_results) == 0:
        break
        
    chunk_df = pd.DataFrame(chunk_results, columns = header)
    chunk_df.to_csv(outfile_name_newinventors, index=False, header=False, mode = 'a', sep='\t')
    
    # continue
    offset+=limit 
    itr+=1

    if itr == 1:
        print('Time for 1 iteration: ', time.time() - start, ' seconds')
    print('###########################################\n')

    
print('###########################################')
print('total time taken:', round(time.time() - start, 2), ' seconds')
print('###########################################')

######### 3. load data
db_con.execute("LOAD DATA LOCAL INFILE '{0}' INTO TABLE {1}.{2} FIELDS TERMINATED BY '\t' IGNORE 1 lines (uuid, database_update, inventor_id);".format(outfile_fp, new_db, 'persistent_inventor_disambig'))

