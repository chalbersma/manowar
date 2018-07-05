#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from configparser import ConfigParser
from colorama import Fore, Back, Style
import time
import argparse
import ast
import pymysql

if __name__ == "__main__":

	parser = argparse.ArgumentParser()
	parser.add_argument("-c", "--config", help="JSON Config File with our Storage Info", required=True)
	parser.add_argument("-V", "--verbose", action="store_true", help="Enable Verbose Mode")
	parser._optionals.title = "DESCRIPTION "

	# Parser Args
	args = parser.parse_args()

	# Grab Variables
	CONFIG=args.config
	VERBOSE=args.verbose
	
def archive_collections(CONFIG, VERBOSE) :

	# Process Config
	try:
		# Read Our INI with our data collection rules
		config = ConfigParser()
		config.read(CONFIG)
	except Exception as e: # pylint: disable=broad-except, invalid-name
		sys.exit('Bad configuration file {}'.format(e))

	# Grab me Collections Items Turn them into a Dictionary
	config_items=dict()

	# Collection Items
	for section in config :
		config_items[section]=dict()
		for item in config[section]:
			config_items[section][item] = config[section][item]
			
	if VERBOSE:
		print("Config Items: ", config_items)

	do_archive = True
	
	try : 
		# Note that Autocommit is off
		db_conn = pymysql.connect(host=config_items["database"]["dbhostname"], port=int(config_items["database"]["dbport"]), \
															user=config_items["database"]["dbusername"], passwd=config_items["database"]["dbpassword"], \
															db=config_items["database"]["dbdb"], autocommit=True )
	except Exception as e :
		# Error
		print("Error Connecting to Datbase with error: ", str(e) )
		do_archive = False
		
	if do_archive == True :
		
		# Set Archive Time
		ARCHIVE_TIME = int(time.time())
		if VERBOSE:
			print("Archive Time: " , str(ARCHIVE_TIME))
		
		# Create Query Strings
		populate_archive_sql = "REPLACE INTO collection_archive SELECT * FROM collection WHERE " +\
														"last_update < FROM_UNIXTIME(" + str(ARCHIVE_TIME) + ") -  interval 7 DAY; "									
		
		remove_overachieving_sql = " DELETE FROM collection WHERE last_update < FROM_UNIXTIME(" + str(ARCHIVE_TIME) + ") - interval 7 DAY; "
		
		'''
		# Not Yet Implemented
		populate_acoll_archive_sql = "REPLACE INTO audits_by_acoll_archive SELECT * FROM audits_by_acoll WHERE " +\-
																	"acoll_last_audit < FROM_UNIXTIME(" + str(ARCHIVE_TIME) + ") -  interval 91 DAY; "
																	
		remove_overachieving_acoll_sql = " DELETE FROM audits_by_acoll_archive WHERE acoll_last_audit < FROM_UNIXTIME(" + str(ARCHIVE_TIME) + ") - interval 91 DAY;"
		'''
		
		cur = db_conn.cursor()
		
		if VERBOSE:
			print(populate_archive_sql)
			print(remove_overachieving_sql)
		
		success = True
		
		try:
			cur.execute(populate_archive_sql)
			new_rows = cur.rowcount
		except Exception as e :
			if VERBOSE:
				print(Fore.RED, "Trouble with archiving query ", str(populate_archive_sql) , " error : ", str(e), Style.RESET_ALL)
			success = False
		else : 
			# Worked So Do the 
			try :
				cur.execute(remove_overachieving_sql)
				removed_rows = cur.rowcount
			except Exception as e :
				if VERBOSE: 
					print(Fore.RED, "Trouble with collection removal query ", str(remove_overachieving_sql) , " error : ", str(e), Style.RESET_ALL)
				success = False
		
		if success == True :
			print(Fore.GREEN, "Collection Table Archived", str(new_rows), " | ", str(removed_rows), Style.RESET_ALL)
		else :
			print(Fore.RED, "Archiving has failed" , Style.RESET_ALL)

if __name__ == "__main__":
	archive_collections(CONFIG, VERBOSE)
