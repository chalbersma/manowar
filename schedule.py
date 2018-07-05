#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import csv
import argparse
from configparser import ConfigParser
from collector import collector
from storage import storage
import json

# For Collection
import socket
import paramiko


# Multithreaded stuff
import threading
from queue import Queue
import time

# Schedule CSV Script
if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument("-c", "--configfile", help="Config File for Scheduler", required=True)
	parser.add_argument("-b", "--batchcsv", help="Use the CSV File to Check all the servers noted. (cannot use -s)")
	parser.add_argument("-o", "--onehost", action='store_true', help="Check just one host (cannot use -b with this)")
	parser.add_argument("-t", "--hostname", help="Check this hostname. If checking a single host this is required. If using -b this is ignored")
	parser.add_argument("-s", "--srvtype", help="Srvtype for the host. Ignored if -b is being used")
	parser.add_argument("-p", "--pop", help="Pop for the host. Ignored if -b is being used")
	parser.add_argument("-m", "--status", help="Status for the host. Ignored if -b is being used")
	parser.add_argument("-i", "--uberid", help="UberID for the host. Ignored if -b is being used (Currently Ignored All the time too)")
	parser.add_argument("-V", "--verbose", action='store_true', help="Verbose Mode Show more Stuff")
	parser._optionals.title = "DESCRIPTION "

	args = parser.parse_args()

	CONFIG=args.configfile

	def parse_csv(csvfile):
		csvfile_object = open(csvfile, 'r')
		hosts = csv.reader(csvfile_object)
		return_hosts = []
		for host in hosts :
			return_hosts.append(host)
		#print(return_hosts)
		return return_hosts

	# Turn on Verbose Mode if Desired
	if args.verbose == True :
		VERBOSE=True
	else :
		VERBOSE=False

	#print(args.hostname)
	# Massage Configdir to not include trailing /
	if args.batchcsv and args.onehost : 
		print("Error, Specifiy only -b or -o not both")
		exit(1)
	elif args.onehost and not args.hostname :
		print("Error, When specifiying one host you need to tell me the host with the -t/--hostname flag")
		exit(2)
	elif not args.batchcsv  and not args.onehost :
		print("Error, Need some hosts to check")
		exit(3)
	elif args.batchcsv : 
		do_csv_parse = True
		csvfile = args.batchcsv
		hosts = parse_csv(csvfile)
	elif args.onehost :
		do_csv_parse = False
		hosts = []
		# No notes as notes are ignored
		onehost = [ args.hostname , args.srvtype, args.pop, args.status, None ]
		hosts.append(onehost)
		
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
			config_items[section][item] = config[section][item]
	
	
def schedule(hosts, config_items): 
	
	global glbl_success_hosts
	global glbl_fail_hosts
	global glbl_fail_hosts_prod
	glbl_success_hosts = list()
	glbl_fail_hosts = list()
	glbl_fail_hosts_prod = list()
	
	schedule_stats = dict()
	
	# how many threads we'll run concurrently
	THREADS = int(config_items["collector"]["threads"])
	# how long we'll allow the full thing to run
	MAXRUNTIME= int(config_items["collector"]["threadtimeout"])
	
	# Find out how and where to store output to
	if config_items["results"]["output_json_file"] == "TRUE" :
		json_out = ( True, config_items["results"]["result_json"] )
	else:
		json_out = ( False, "/dev/null" )
		
	schedule_stats["threads"]=THREADS
	
	# collector(HOST, CONFIG, USERNAME, KEYFILE, POP, SRVTYPE, UBERID, STATUS, IPV4, IPV6, APPEND)
		
	# Print Lock so we Only print one thing to the screen at a time
	print_lock = threading.Lock()
	# Only want one process updating our counters at a time
	counter_lock = threading.Lock()
	
	# Work Function ( host array, config_items
	def process_one_host(host_array, config_dict) : 
		
		# Grab my Literals
		hostname=host_array[0]
		srvtype=host_array[1]
		pop=host_array[2]
		status=host_array[3]
		# I Never have an uber id in the scheduler
		# Feature is not yet supported
		uberid="N/A"
	
		# For Missing Data
		if pop is None:
			pop = "N/A"
		if srvtype is None:
			srvtype = "N/A"
		if status is None:
			status = "N/A"
			
		username=config_dict["paramiko"]["paramiko_user"]
		keyfile=config_dict["paramiko"]["paramiko_key"]
		collector_config_file=config_dict["collector"]["collconfig"]
		storage_config_file=config_dict["storage"]["storeconfig"]
		#print(keyfile)
		
		# Process our IPV4/6 Options
		if config_dict["paramiko"]["ipv4"] in ["TRUE", "true", "True", "Yes", "yes"] :
			ipv4=True
			ipv6=False
		elif config_dict["paramiko"]["ipv6"] in ["TRUE", "true", "True", "Yes", "yes"] :
			ipv6=True
			ipv4=False
		else :
			# Pass it up the stack (Generally use hostname)
			ipv6=False
			ipv4=True
			
		if config_dict["paramiko"]["edgecast_append"] in ["TRUE", "true", "True", "Yes", "yes"] :
			append=True
		else : 
			append=False
		
		
		#Do Collection
		try:
			this_host_collection_result = collector(hostname, collector_config_file, username, keyfile, pop, srvtype, uberid, status, ipv4, ipv6, append)
		except Exception as e:
			print("Error Collecting host : " , hostname , " With Error : ", e )
			this_host_collection_result["true_failure"] = True
		
		#with print_lock:
			#print(this_host_collection_result)
		
		collection_host_failures = False
		collection_host_failures_prod = False
		collection_host_success = False
		
		if "true_failure" in this_host_collection_result.keys() :
			# Failed to Collect Our Data Update our Counters
			collection_host_failures = True
			
			if status == "prod" :
				collection_host_failures_prod = True

		else : 
			# No Failure
			collection_host_success = True
				
			# I'm good and have recorded the collection's success. Let's attempt to store
			# storage(CONFIG, JSONFILE):
			this_store_collection_result = storage(storage_config_file, this_host_collection_result)
			if this_store_collection_result["db-status"] == "Connection Failed" :
				# Failed to Store Item.
				collection_host_success = False
		
		return collection_host_success, collection_host_failures, collection_host_failures_prod	
		
			
	# Pull data off of the host_queue queue
	def dequeue_hosts(config_array):
		while True:
			# Pull Stats Stuff
			# Pull Enqueued Host
			this_one_host_array = host_queue.get()
			#print("Pulled Host ", this_one_host_array)
			# Process One Host Pass it the host_array and the config_array
			try :
				success, fail, fail_prod = process_one_host(this_one_host_array, config_array)
			except :
				# It's a Failure
				success=False
				fail=True
				# If it's aprod host note it here
				if this_one_host_array[3] == "prod":
					fail_prod = True
			try:
				if counter_lock.acquire(timeout=2) :
					# Debug
					if VERBOSE :
						# If Verbose Mode Echo this Out
						print("Finished Host:", this_one_host_array[0])
					if success :
						glbl_success_hosts.append(this_one_host_array[0])
					elif fail :
						glbl_fail_hosts.append(this_one_host_array[0])
						if fail_prod :
							glbl_fail_hosts_prod.append(this_one_host_array[0])
				else :
					if VERBOSE :
						print("Finished Host:", this_one_host_array[0], "But unable to acquire write lock")
			except :
				print("Error recording host", this_one_host_array[0])
			finally:
				counter_lock.release()
			
			# Dequeue the Host from host_queue
			host_queue.task_done()
		return
			
	# Create a Queue for our hosts to live in.
	host_queue = Queue(maxsize=0)
	
	# Collection Threads
	for x  in range(THREADS) :
		# Set THread Target Always pass it our config_array
		t  = threading.Thread(target=dequeue_hosts, args=(config_items,))
		# Make Threads Die if Parent is Killed
		t.daemon = True
		# Start my Threads
		t.start()
		
	# Record When Enqueing Started
	start = time.time()
	
	# Toss Host on Queue
	# Debug Creating A Counter To Print on Host Placement in Queue
	#host_position=0
	#everyx=100
	for host in hosts :
		# Place the Host on the Queue
		host_queue.put(host)
		# Incrment my Host_position
		#host_postion = host_position + 1
		# If it's an everyx'ed host_position Print me back to the screen
		#if host_position % everyx == 0 :
		#	print("On Host: ", host_position, " Named : ", host[0] )
		# No matter what move to the next host

	# 
	
	# Wait until Unfinished Tasks is less than 10
	while host_queue.unfinished_tasks > 0 :
		# If Verbose Give me Stats
		if VERBOSE :
			print("---------------------------------------")
			print("HostsLeft \t QSize \t Thread \t QStuff ")
			print(host_queue.unfinished_tasks, "\t\t", host_queue.qsize(), "\t", threading.active_count(), "\t\t", host_queue.empty() )
			print("---------------------------------------")
		
		# Implement Timeout Logic
		current_run_time = time.time() - start
		if current_run_time > MAXRUNTIME :
			schedule_stats["Timeout"] = "Timeout reached at " + str(current_run_time) + " seconds with " + str(host_queue.unfinished_tasks) + " items left on the queue."
			break
		
		# Sleep 30 Seconds
		time.sleep(30)
		
	# Wait for Queue to finish Processin
	
	# host_queue.join()
	
	# Store Stats Values
	schedule_stats["global_success_hosts_list"] = glbl_success_hosts
	schedule_stats["global_success_hosts"] = len(glbl_success_hosts)
	schedule_stats["global_fail_hosts_list"] = glbl_fail_hosts
	schedule_stats["global_fail_hosts"] = len(glbl_fail_hosts)
	schedule_stats["global_fail_prod_list"] = glbl_fail_hosts_prod
	schedule_stats["global_fail_prod"] = len(glbl_fail_hosts_prod)
	schedule_stats["jobtime"] = "Entire job took:" + str(time.time() - start)
	
	if __name__ == "__main__" :
		print(json.dumps(schedule_stats, sort_keys=True, indent=4))
		
	if json_out[0] == True :
		with open(json_out[1], 'w') as json_out_file :
			json_out_file.write(json.dumps(schedule_stats, sort_keys=True, indent=4))
		
	return schedule_stats

if __name__ == "__main__":
	schedule(hosts, config_items)	
