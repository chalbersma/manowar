#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# gap_fix.py

# A lower intensity scheduler designed to find prod hosts that didn't
# make it into the last collection and try them again but with a lower
# Intensity so normal operations can continue throughout the day.

# Generally needed for storage stuff
import csv
import argparse
from configparser import ConfigParser
from collector import collector
from storage import storage
import json

# Gap Fix Specific
import pymysql
import ast
from schedule2 import schedule

# For Collection
import socket
import paramiko

# Multithreaded stuff
import multiprocessing
import queue
import sys
import time

# For OS Interaction
import os
import signal


# User Colors (For the nicestest)
from colorama import Fore, Back, Style
import pprint

# For SAPI Check
from sapicheck import grab_all_sapi

# Random Numbers
import random
if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-c", "--configfile", help="Config File for Scheduler", required=True)
	parser.add_argument("-f", "--findonly", action='store_true', help="Find (and print) the missing hosts do not action.")
	parser.add_argument("-V", "--verbose", action='store_true', help="Verbose Mode Show more Stuff")
	
	args = parser.parse_args()

	CONFIG=args.configfile

	def parse_and_filter_csv(csvfile, status_filter="prod"):
		csvfile_object = open(csvfile, 'r')
		hosts = csv.reader(csvfile_object)
		return_hosts = []
		for host in hosts :
			if host[3] == status_filter : 
				return_hosts.append(host)

		return return_hosts

	if args.verbose == True :
		VERBOSE=True
	else :
		VERBOSE=False
		
	if args.findonly == True : 
		DO_SCHED=False
	else : 
		DO_SCHED=True
	
	try:
		# Read Our INI with our data collection rules
		config = ConfigParser()
		config.read(CONFIG)
		# Debug
		#for i in config : 
			#for key in config[i] : 
				#print (i, "-", key, ":", config[i][key])
	except Exception as e: # pylint: disable=broad-except, invalid-name
		sys.exit('Bad configuration file {}'.format(e))

	# Grab me Collections Items Turn them into a Dictionary
	config_items=dict()

	# Collection Items
	for section in config :
		config_items[section]=dict()
		for item in config[section]:
			config_items[section][item] = ast.literal_eval(config[section][item])	

	hosts = parse_and_filter_csv(config_items["gapfix"].get("ubercsv", "/oc/local/netinfo/etc/servers4.csv"))
	
def find_gaps(config, uber_hosts, do_sched=True, verbose=False) :
	
	### Grab a list of hosts from the database
	
	# Get a DB Connection
	try:
		db_conn = pymysql.connect(host=config['database']['dbhostname'], port=int(config['database']['dbport']), user=config['database']['dbusername'], passwd=config['database']['dbpassword'], db=config['database']['dbdb'] )
		dbmessage = "Good, connected to " + config['database']['dbusername'] + "@" + config['database']['dbhostname'] + ":" + config['database']['dbport'] + "/" + config['database']['dbdb']
		db_cursor = db_conn.cursor(pymysql.cursors.DictCursor)
	except Exception as e:
		print("Gap Ananlysis Failed Grabbing Current Hosts on DB Connection : " , str(e))
		sys.exit(1)
	else : 
		
		# How far back to check. Should be 24 hours.
		all_current_hosts = "select hostname from hosts where last_update >= (now() - INTERVAL 2 DAY) "
	
		try:
			db_cursor.execute(all_current_hosts)
				
			results = db_cursor.fetchall()
		except Exception as e : 
			print("Grab all Current Hosts failed with" , str(e))
			sys.exit(1)
		else : 
			
			db_cursor.close()
			all_active_hosts = list()
			for host in results : 
				# Pop host onto array
				all_active_hosts.append(host["hostname"])
	
	
		# Compare the list given with the Host in Jellyfish
		gap_hosts = [ host for host in uber_hosts if host[0] not in all_active_hosts ] 
		
	# Start a Low Thread (12?) schedule2.py process and attempt to collect
	# those missing hosts.
	# Thread count controlled by gap_fix.ini
	
	if do_sched == True :
		print("Staring Gap Schedule")
		schedule(gap_hosts, config, VERBOSE=verbose)
	else : 
		gap_dict = dict()
		gap_dict["found_gap"] = len(gap_hosts)
		gap_dict["gap_hosts"] = gap_hosts
		print(json.dumps(gap_dict))
	
	
	# Report those that still fail.
	
if __name__ == "__main__":
	
	# find gaps
	find_gaps(config_items, hosts, do_sched=DO_SCHED, verbose=VERBOSE)
