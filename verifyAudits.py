#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# verifyAudits.py - Designed to verify that all of our audit files
# are good to go.


# Run through Analysis
import os

import ast
import argparse
import sys
from time import time

from configparser import ConfigParser

if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-a", "--auditdir", help="Directory that Contains the audits", required=True)
	#parser.add_argument("-c", "--config", help="Main analyze.ini file", required=True)
	parser._optionals.title = "DESCRIPTION "

	# Parser Args
	args = parser.parse_args()

	# Massage Configdir to not include trailing /
	if args.auditdir[-1] == "/" :
		CONFIGDIR=args.auditdir[0:-1]
	else : 
		CONFIGDIR=args.auditdir

	# 
	#CONFIG=args.config

def verifySingleAudit(auditfile) : 

	field_strings = [ "vuln-name", "vuln-short-description", "vuln-primary-link", "vuln-long-description" ]
	field_ints = [ "vuln-priority", "now", "monthago", "threeyearago", "quarterago", "weekago", "yearago" ]
	field_dicts = [ "vuln-additional-links", "filters", "comparisons" ]
	all_fields = field_strings + field_ints + field_dicts
	total_fields = len(all_fields)
	
	fields_checked = []

	verified=True

	# Config Defaults
	this_time=int(time())
	back_week=this_time-604800
	back_month=this_time-2628000
	back_quarter=this_time-7844000
	back_year=this_time-31540000
	back_3_year=this_time-94610000
	time_defaults={ "now" : str(this_time), "weekago" : str(back_week), "monthago" : str(back_month), "quarterago" : str(back_quarter), "yearago" : str(back_year), "threeyearago" : str(back_3_year) }

	try:
		# Try to Parse
		this_audit_config = ConfigParser(time_defaults)
		this_audit_config.read(auditfile)
	except Exception as e: 
		# Error if Parse
		print("File ", auditfile, " not paresed because of " , format(e))
		verified=False
	else:
	# It's good so toss that shit in
		for section in this_audit_config : 
			# I let "Global or Default" fly right now
			if section not in ["GLOBAL", "DEFAULT"] :
							
				##### Parse Check ########
				filter_object = dict()
				comparison_object = dict()
				
				for item in this_audit_config[section]:
					fields_checked.append(item)
					#print(item)
					onelinethisstuff = "".join(this_audit_config[section][item].splitlines())
					try:
					    if item == "vuln-long-description" :
					        parsed = ast.literal_eval("'''{}'''".format(onelinethisstuff))
					    else
					        parsed = ast.literal_eval(onelinethisstuff)
					except Exception as e:
						print("Issue with file ", auditfile, " when attempting to parse", item, "Error ", str(e), onelinethisstuff)
						verified=False
					
					if item in field_strings :
						if type(parsed) is not str:
							print("Issue with file ", auditfile, " when attempting to parse", item, " Type is not String but instead " , type(parsed) )
							verified=False
					elif item in field_ints :
						if type(parsed) is not int :
							print("Issue with file ", auditfile, " when attempting to parse", item, " Type is not Int but instead " , type(parsed) )
							verified=False
					elif item in field_dicts : 
						if type(parsed) is not dict :
							print("Issue with file ", auditfile, " when attempting to parse", item, " Type is not dict but instead " , type(parsed) )
							verified=False
						if item is "filters" :
							filter_object = parsed
						if item is "comparisons" : 
							comparison_object = parsed
					else :
						# Auto Error unkown Field
						print("Issue with file ", auditfile, " when attempting to parse", item, " Unkown Field ")
						verified=False
					
				## Compare buckets
				comparison_okay = [ bucket for bucket in comparison_object.keys() if bucket not in filter_object.keys() ]
				filter_okay = [ bucket for bucket in comparison_object.keys() if bucket not in filter_object.keys() ]
				
				if len(comparison_okay) > 0 or len(filter_okay) > 0 : 
					print("Issue with file ", auditfile, " Comparison and bucket items. Bad filters = ",  str(filter_okay), " Bad comparisons ", str(comparison_okay) )
					verified=False
	
	## Check Counts
	if len(fields_checked) != total_fields :
		missing_fields = [ field for field in all_fields if field not in fields_checked ]
		extra_fields = [ field for field in fields_checked if field not in all_fields ]
		
		print("Issue with file ", auditfile, "Field Error(s). Extra Fields : " , str(extra_fields), " ; Missing Fields : ", str(missing_fields) )
		verified=False
	
	return verified

def verifyAudits(CONFIGDIR, CONFIG=None):
	
	currently_verified=True
	
	# Config Defaults
	this_time=int(time())
	back_week=this_time-604800
	back_month=this_time-2628000
	back_quarter=this_time-7844000
	back_year=this_time-31540000
	back_3_year=this_time-94610000
	time_defaults={ "now" : str(this_time), "weekago" : str(back_week), "monthago" : str(back_month), "quarterago" : str(back_quarter), "yearago" : str(back_year), "threeyearago" : str(back_3_year) }

	'''
	try:
		# Read Our INI with our data collection rules
		config = ConfigParser(time_defaults)
		config.read(CONFIG)
		# Debug
		#for i in config : 
			#for key in config[i] : 
				#print (i, "-", key, ":", config[i][key])
	except Exception as e: # pylint: disable=broad-except, invalid-name
		print("Bad configuration file")
		currently_verified=False
	'''
		
	
	# Grab all my Audits in CONFIGDIR Stuff
	auditfiles = []
	for (dirpath, dirnames, filenames) in os.walk(CONFIGDIR) : 
		for singlefile in filenames : 
			onefile = dirpath + "/" +  singlefile
			#print(singlefile.find(".ini", -4))
			if singlefile.find(".ini", -4) > 0 : 
				# File ends with .ini Last 4 chars
				auditfiles.append(onefile)
				
		# Parse the Dicts
	#audits=dict()
	for auditfile in auditfiles : 
		if verifySingleAudit(auditfile) == False:
			currently_verified=True
			
	return currently_verified

	
if __name__ == "__main__":
	okay = verifyAudits(CONFIGDIR)

	if okay == True :
		print("Audits Okay")
		sys.exit(0)
	else :
		print("Audits checks Failed")
		sys.exit(1)
	
