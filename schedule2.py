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
import multiprocessing
import queue
import sys
import time

import os
import signal


# User Colors
from colorama import Fore, Back, Style
import pprint

from sapicheck import grab_all_sapi

# Random Numbers
import random


# Schedule CSV Script
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", help="Config File for Scheduler", required=True)
    parser.add_argument("-b", "--batchcsv", help="CSV File with Hosts (servers4.csv)")
    parser.add_argument("-o", "--onehost", action='store_true', help="Check just one host")
    parser.add_argument("-t", "--hostname", help="Hostname to check (single only).")
    parser.add_argument("-s", "--srvtype", help="Srvtype of host (single only)")
    parser.add_argument("-p", "--pop", help="Pop for the host. (single only)")
    parser.add_argument("-m", "--status", help="Status for the host. (single only)")
    parser.add_argument("-i", "--uberid", help="UberID for the host. (ignored)")
    parser.add_argument("-V", "--verbose", action='store_true', help="Verbose Mode Show more Stuff")
    parser._optionals.title = "DESCRIPTION "

    args = parser.parse_args()

    CONFIG = args.configfile

    def parse_csv(csvfile):
        csvfile_object = open(csvfile, 'r')
        hosts = csv.reader(csvfile_object)
        priority_hosts = list()
        secondary_hosts = list()
        for host in hosts:
            if host[3] == "prod":
                priority_hosts.append(host)
            else:
                secondary_hosts.append(host)

        # Shuffle My Priority Hosts so that
        print(Fore.GREEN, "Shuffling Priority Hosts.", Style.RESET_ALL)
        random.shuffle(priority_hosts)
        print(Fore.GREEN, "...Shuffling Done.", Style.RESET_ALL)

        # Make me try the shuffled prod hosts before the rest
        return_hosts = priority_hosts + secondary_hosts

        return return_hosts

    # Turn on Verbose Mode if Desired
    if args.verbose == True:
        VERBOSE = True
    else:
        VERBOSE = False

    #print(args.hostname)
    # Massage Configdir to not include trailing /
    if args.batchcsv and args.onehost:
        print("Error, Specifiy only -b or -o not both")
        exit(1)
    elif args.onehost and not args.hostname:
        nohostname_error_msg = "Error, When specifiying one host you need to tell" + \
                             "me the host with the -t/--hostname flag"
        print(nohostname_error_msg)
        exit(2)
    elif not args.batchcsv  and not args.onehost:
        print("Error, Need some hosts to check")
        exit(3)
    elif args.batchcsv:
        do_csv_parse = True
        csvfile = args.batchcsv
        hosts = parse_csv(csvfile)
    elif args.onehost:
        do_csv_parse = False
        hosts = []
        # No notes as notes are ignored
        onehost = [args.hostname, args.srvtype, args.pop, args.status, None]
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
    config_items = dict()

    # Collection Items
    for section in config:
        config_items[section] = dict()
        for item in config[section]:
            config_items[section][item] = config[section][item]


def schedule(hosts, config_items, VERBOSE=False):

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
    MAXRUNTIME = int(config_items["collector"]["threadtimeout"])

    # Find out how and where to store output to
    if config_items["results"]["output_json_file"] == "TRUE":
        json_out = (True, config_items["results"]["result_json"])
    else:
        json_out = (False, "/dev/null")

    schedule_stats["threads"] = THREADS

    # collector(HOST, CONFIG, USERNAME, KEYFILE, POP, SRVTYPE, UBERID, STATUS, IPV4, IPV6, APPEND)

    # Print Lock so we Only print one thing to the screen at a time
    print_lock = multiprocessing.Lock()
    # Only want one process updating our counters at a time
    counter_lock = multiprocessing.Lock()

    # Work Function ( host array, config_items
    def process_one_host(host_array, config_dict):

        # Grab my Literals
        hostname = host_array[0]
        srvtype = host_array[1]
        pop = host_array[2]
        status = host_array[3]
        # I Never have an uber id in the scheduler
        # Feature is not yet supported
        uberid = "N/A"

        # For Missing Data
        if pop is None:
            pop = "N/A"
        if srvtype is None:
            srvtype = "N/A"
        if status is None:
            status = "N/A"

        username = config_dict["paramiko"]["paramiko_user"]
        keyfile = config_dict["paramiko"]["paramiko_key"]
        collector_config_file = config_dict["collector"]["collconfig"]
        storage_config_file = config_dict["storage"]["storeconfig"]
        #print(keyfile)

        # Process our IPV4/6 Options
        if config_dict["paramiko"]["ipv4"] in ["TRUE", "true", "True", "Yes", "yes"]:
            ipv4 = True
            ipv6 = False
        elif config_dict["paramiko"]["ipv6"] in ["TRUE", "true", "True", "Yes", "yes"]:
            ipv6 = True
            ipv4 = False
        else:
            # Pass it up the stack (Generally use hostname)
            ipv6 = False
            ipv4 = True

        if config_dict["paramiko"]["edgecast_append"] in ["TRUE", "true", "True", "Yes", "yes"]:
            append = True
        else:
            append = False


        #Do Collection
        this_host_collection_result = collector(hostname, collector_config_file, \
                                                username, keyfile, pop, srvtype, \
                                                uberid, status, ipv4, ipv6, append)

        collection_host_failures = False
        collection_host_failures_prod = False
        collection_host_success = False


        if "true_failure" in this_host_collection_result.keys():
            # Failed to Collect Our Data Update our Counters
            collection_host_failures = True
            print("Failure to collect: ", this_host_collection_result)

            if status == "prod":
                collection_host_failures_prod = True
        else:
            # No Failure
            try:
                if VERBOSE:
                    print(Back.WHITE, Fore.BLACK, "Storage for ", hostname, Style.RESET_ALL)
                this_store_collection_result = storage(storage_config_file, \
                                                       this_host_collection_result)

                collection_host_success = True
            except Exception as e: # pylint: disable=broad-except, invalid-name

                print(Fore.RED, "Error In Storage module", str(e), \
                      "Storage of ", hostname, "Failed", Style.RESET_ALL)

                collection_host_success = False
            else:
                if this_store_collection_result["db-status"] == "Connection Failed":
                    # Failed to Store Item.
                    print(Back.RED, Fore.WHITE, "Failed to store results for ", \
                          hostname, " Error: ", \
                          str(this_store_collection_result["db-error"]), \
                          Style.RESET_ALL)
                    pprint.pprint(this_store_collection_result)
                    collection_host_success = False
                elif this_store_collection_result["collection_status"] == True:
                    pass
            finally:
                pass

        if VERBOSE:
            print(Fore.BLACK, Back.YELLOW, "Host : ", hostname, \
                  "P-O-H Results : ", collection_host_success, \
                  collection_host_failures, collection_host_failures_prod, \
                  Style.RESET_ALL)
        return collection_host_success, collection_host_failures, collection_host_failures_prod


    # Pull data off of the host_queue queue
    def dequeue_hosts(thread_num, host_queue, result_queue, config_array):
        while True:
            # Pull Stats Stuff
            # Pull Enqueued Host

            # Nosecc'ed this isn't being used for cryptography but for statistical
            # Modeling. B311 doesn't apply here.
            do_flush_int = random.randint(0, 20) # nosec
            # Only Flush buffers on every 20th (ish) host
            if do_flush_int == 0:
                sys.stdout.flush()

            if host_queue.empty() == False:
                try:
                    this_one_host_array = host_queue.get(timeout=3)

                    if VERBOSE:
                        print(Fore.GREEN, "Pulled Host ", this_one_host_array, \
                              "in thread", str(thread_num), Style.RESET_ALL)

                except Exception as e: # pylint: disable=broad-except, invalid-name
                    print(Fore.RED, "Could not pull host off queue ending thread # ", \
                          str(thread_num), " Error : ", str(e), Style.RESET_ALL)
                    break
                else:

                    try:

                        results_tuple = process_one_host(this_one_host_array, \
                                                         config_array)

                        success = results_tuple[0]
                        fail = results_tuple[1]
                        fail_prod = results_tuple[2]

                    except Exception as e: # pylint: disable=broad-except, invalid-name
                        # It's a Failure
                        print("Failure to process_one_host for host", \
                              str(this_one_host_array), " with error ", str(e))
                        success = False
                        fail = True
                        # If it's aprod host note it here
                        if this_one_host_array[3] == "prod":
                            fail_prod = True
                        else:
                            fail_prod = False
                    finally:

                        if VERBOSE and success == True:

                            print(Fore.GREEN, "Host : ", this_one_host_array, \
                                  " Results ", success, fail, fail_prod, \
                                  Style.RESET_ALL)

                        elif VERBOSE and success == False:

                            print(Fore.RED, "Host : ", this_one_host_array, \
                                  " Results ", success, fail, fail_prod, \
                                  Style.RESET_ALL)

                        result_list = (this_one_host_array, success, fail, fail_prod)


                        try:
                            result_queue.put(result_list)
                            print(Fore.GREEN, "Placed on Queue: ", result_list, Style.RESET_ALL)
                        except Exception as e: # pylint: disable=broad-except, invalid-name

                            print(Fore.RED, "Error Placing results for host ", \
                                  this_one_host_array[0], " On Result Queue ", \
                                  Style.RESET_ALL)

                        finally:
                            # For future stuff
                            pass
            else:

                print(Style.DIM, "Queue empty breaking thread loop. Thread: ", \
                      str(thread_num), Style.RESET_ALL)

                break

        my_pid = multiprocessing.current_process().pid
        if VERBOSE:

            print(Style.DIM, "Ending Thread", str(thread_num), " PID: ", \
                  my_pid, Style.RESET_ALL)

        #result_queue.close()
        #result_queue.join_thread()
        # End of Thread always Flush
        sys.stdout.flush()

        try:
            os.kill(my_pid, signal.SIGTERM)
        except Exception as e: # pylint: disable=broad-except, invalid-name
            print(Style.RED, "Error committing suicide Thread", str(thread_num), \
                  " PID: ", my_pid, Style.RESET_ALL)

        return


    # Create my Manager Object
    manager = multiprocessing.Manager()

    # Create a Queue for our hosts to live in.
    host_queue = manager.Queue(maxsize=0)

    # Results Queue
    result_queue = manager.Queue()



    # Record When Enqueing Started
    start = time.time()

    sapi_hosts_list = list()

    found_sapi_hosts = grab_all_sapi(config_items["storage"]["storeconfig"])

    # Toss Host on Queue
    for host in hosts:

        # Check if Host is a SAPI host

        if host[0] in found_sapi_hosts:
            # Don't place on Queue, I've found you as a sapi host.
            sapi_hosts_list.append(host[0])

            print(Style.DIM + "Host ", host[0], \
                  " is a sapi host. Not placing on queue.", Style.RESET_ALL)

        else:
            # Place the Host on the Queue
            host_queue.put(host)
            # Incrment my Host_position
            #host_postion = host_position + 1
            # If it's an everyx'ed host_position Print me back to the screen
            #if host_position % everyx == 0 :
            #   print("On Host: ", host_position, " Named : ", host[0] )
            # No matter what move to the next host

    # Allows muliprocess queue to settle
    time.sleep(5)
    thread_array = dict()



    # Take Hosts Off Queue
    for x  in range(THREADS):
        # Set THread Target Always pass it our config_array
        if host_queue.empty() == False:
            if VERBOSE:
                print(Style.DIM + "Provisioning thread number: ", str(x), Style.RESET_ALL)

            try:

                thread_array[x] = multiprocessing.Process(target=dequeue_hosts, \
                                    args=(x, host_queue, result_queue, config_items))

                # Make Threads Die if Parent is Killed
                thread_array[x].daemon = True
                # Start my Threads
                thread_array[x].start()
            except Exception as e: # pylint: disable=broad-except, invalid-name
                print("Error with thread:", str(e))
            finally:
                if x < 50:
                    # Always sleep for first 50 threads
                    time.sleep(1)
                elif x % 7 == 0:
                    # Do new threads 7 at a time
                    time.sleep(1)

        else:

            print(Style.DIM + "Queue is Empty Stopping allocation at: ", str(x), \
                  " threads ", Style.RESET_ALL)

            break

    if VERBOSE:

        print(Style.DIM, Fore.MAGENTA, Back.CYAN, "All Threads Allocated", \
              Style.RESET_ALL)

    # Wait until Unfinished Tasks is less than 10
    current_check_iteration = 0

    while True:
        # Check if were past our timeout
        current_run_time = time.time() - start
        if current_run_time < MAXRUNTIME:
            current_check_iteration += 1
            if (current_check_iteration % 250) == 0:
                FULL_PRINT = True
                if VERBOSE:
                    print("Iteration : ", current_check_iteration, " Printing PID List ")
            else:
                FULL_PRINT = False

            any_threads_alive = False
            threads_finished = 0
            threads_running = 0
            for thread in thread_array.keys():
                # If the Thread is Alive
                if thread_array[thread].is_alive() == True:
                    any_threads_alive = True
                    threads_running += 1
                    if VERBOSE and FULL_PRINT:

                        print("Running Thread", thread, " pid ", \
                              thread_array[thread].pid)

                else:
                    # Can Print Finished Threads
                    threads_finished += 1
                    pass

            # Always VERBOSE Print
            if VERBOSE and FULL_PRINT:

                print("T: ", Style.BRIGHT, str(int(current_run_time)), \
                        Style.RESET_ALL, " RThreads: ", Fore.GREEN, \
                        str(threads_running), Style.RESET_ALL, " FThreads: ", \
                        Fore.CYAN, str(threads_finished), Style.RESET_ALL, \
                        "HostsLeft: ", Back.CYAN, Fore.BLACK, \
                        str(host_queue.qsize()), Style.RESET_ALL, "Results: ", \
                        Fore.GREEN, str(result_queue.qsize()), Style.RESET_ALL)

            if any_threads_alive == False:
                # Break While Loop
                break
            else:
                # Continue
                pass
        else:

            # Timeout Has Been Reached
            schedule_stats["Timeout"] = "Timeout reached at " + \
                        str(current_run_time) + " seconds with " + \
                        str(host_queue.qsize()) + " items left on the queue."

            if VERBOSE:
                print(Fore.BLUE, Back.CYAN, "TIMEOUT", schedule_stats["Timeout"], Style.RESET_ALL)
            break
        # Sleep 20 seconds and try again
        time.sleep(20)

    # Let result_queue settle
    time.sleep(5)

    # Adjust Count By Failure_Adjustment for failed Pulls off Queue.
    failure_adjustment = 0
    current_count = result_queue.qsize() - failure_adjustment

    while current_count > 0:

        # Result Queue Isn't Empty Pull Results

        try:
            this_result = result_queue.get(timeout=5)
        except Exception as get_error: # pylint: disable=broad-except, invalid-name
            # Modify Failure Adjustment
            failure_adjustment += 1
            print(Fore.RED + "Error grabbing results. Adjusting Error : " + \
                  str(failure_adjustment) + " Error message : " + \
                  str(get_error) + Style.RESET_ALL)

        else:
            # List Format for Results
            this_one_host_array = this_result[0]
            success = this_result[1]
            fail = this_result[2]
            fail_prod = this_result[3]

            if success:
                glbl_success_hosts.append(this_one_host_array[0])
            elif fail:
                glbl_fail_hosts.append(this_one_host_array[0])
            if fail_prod:
                glbl_fail_hosts_prod.append(this_one_host_array[0])
        finally:
            # Placeholder
            current_count = result_queue.qsize() - failure_adjustment
            #print("Items left on queue: ", current_count )
            pass

    # Store Stats Values
    schedule_stats["global_success_hosts_list"] = glbl_success_hosts
    schedule_stats["global_success_hosts"] = len(glbl_success_hosts)
    schedule_stats["global_fail_hosts_list"] = glbl_fail_hosts
    schedule_stats["global_fail_hosts"] = len(glbl_fail_hosts)
    schedule_stats["global_fail_prod_list"] = glbl_fail_hosts_prod
    schedule_stats["global_fail_prod"] = len(glbl_fail_hosts_prod)
    schedule_stats["sapi_hosts"] = len(sapi_hosts_list)
    schedule_stats["sapi_hosts_list"] = sapi_hosts_list
    schedule_stats["jobtime"] = "Entire job took:" + str(time.time() - start)

    if __name__ == "__main__":
        print(json.dumps(schedule_stats, sort_keys=True, indent=4))

    if json_out[0] == True:
        with open(json_out[1], 'w') as json_out_file:
            json_out_file.write(json.dumps(schedule_stats, sort_keys=True, indent=4))

    return schedule_stats

if __name__ == "__main__":
    schedule(hosts, config_items, VERBOSE=VERBOSE)
