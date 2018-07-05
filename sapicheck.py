#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from colorama import Fore, Back, Style
from configparser import ConfigParser
import pymysql



def grab_all_sapi(CONFIG) : 

	all_hosts = list()

	try:
		config = ConfigParser()
		config.read(CONFIG)
	except Exception as e: # pylint: disable=broad-except, invalid-name	
		print(Back.WHITE, Fore.RED, "Configuration Error on SAPI Check error : " , str(e),  Style.RESET_ALL)
		return False
		

	db_config_items = dict()
	# Get the DB Configuration
	for section in config:
		if section == "database" : 
			for item in config[section]: 
				db_config_items[item] = config[section][item]

	# Get a DB Connection
	try:
		db_conn = pymysql.connect(host=db_config_items['dbhostname'], port=int(db_config_items['dbport']), user=db_config_items['dbusername'], passwd=db_config_items['dbpassword'], db=db_config_items['dbdb'] )
		dbmessage = "Good, connected to " + db_config_items['dbusername'] + "@" + db_config_items['dbhostname'] + ":" + db_config_items['dbport'] + "/" + db_config_items['dbdb']
		db_cursor = db_conn.cursor(pymysql.cursors.DictCursor)
	except Exception as e:
		print(Back.WHITE, Fore.RED, "Grabbing Current SAPI hosts failed with" , str(e),  Style.RESET_ALL)
	else : 
		# Have a db connection now let's move forward to the check
		
		# select * from sapiActiveHosts where hostname = %s and last_updated >= (now() - INTERVAL 3 DAY) limit 1;
		
		all_sapi_hosts_sql = "select hostname from sapiActiveHosts where last_updated >= (now() - INTERVAL 3 DAY) "
	
		try:
			db_cursor.execute(all_sapi_hosts_sql)
				
			results = db_cursor.fetchall()
		except Exception as e : 
			print(Back.WHITE, Fore.RED, "Grab all SAPI failed with" , str(e),  Style.RESET_ALL)
		else : 
			
			db_cursor.close()
				
			for host in results : 
				# Pop host onto array
				all_hosts.append(host["hostname"])
		
	# Retun the hosts I've found, if non will return an empty list.
	return all_hosts



