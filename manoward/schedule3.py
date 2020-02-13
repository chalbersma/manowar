#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

Schedule3.py Take adavantage of a Setup (Hopefully non-root) SaltSSH Environment
And Utilize it to make my SSH based collections.
'''

# Stdlib
from colorama import Fore, Back, Style
import argparse
import logging
import multiprocessing
import queue
import sys
import time
import os
import re
import signal
import random
import hashlib
import json

# Pips
import yaml
import saltcell.clientcollector


# Local
import manoward

from manoward.storage import storage


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", help="Config File for Scheduler", required=False, default=None)
    parser.add_argument(
        "-r", "--regex", help="Only Hosts that Match this Regex", default=None)
    parser.add_argument("-v", "--verbose", action='append_const',
                        help="Turn on Verbosity", const=1, default=[])
    parser.add_argument("-p", "--print", action="store_true",
                        help="Print Results to Screen", default=False)
    parser.add_argument(
        "-s", "--shard", help="Match only This Shard", default=None)

    args = parser.parse_args()

    CONFIG = manoward.get_manoward(explicit_config=args.config,
                                   only_file=False)

    VERBOSE = len(args.verbose)

    if VERBOSE == 0:
        logging.basicConfig(level=logging.ERROR)

    elif VERBOSE == 1:
        logging.basicConfig(level=logging.WARNING)

    elif VERBOSE == 2:
        logging.basicConfig(level=logging.INFO)

    elif VERBOSE > 2:
        logging.basicConfig(level=logging.DEBUG)

    LOGGER = logging.getLogger()

    LOGGER.info("Welcome to Schedule3.py")


def read_hosts(config_items, regex=None, shard=None):
    '''
    Read the roster file (I'ts a Yaml File). And return the dictionary
    of items associated with it.
    '''

    logger = logging.getLogger("schedule3.py:read_hosts")

    roster_file = os.path.join(config_items["schedule"].get(
        "salt_ssh_basedir", "./etc/manowar/salt"), "roster")
    logger.debug(roster_file)

    final_roster = dict()

    with open(roster_file, "r") as roster_file_obj:
        try:
            roster = yaml.safe_load(roster_file_obj)
        except Exception as roster_load_error:
            logger.error(
                "Unable to Read Roster File {}, Yaml Error".format(roster_file))
            logger.debug("Error : {}".format(roster_load_error))
            roster = dict()
        else:

            if isinstance(shard, str):
                logger.info(
                    "Choosing Items that Match Shard : {}".format(shard.upper()))

                sharded_roster = dict()
                for roster_id, roster_args in roster.items():
                    this_hash = hashlib.sha256(roster_id).hexdigest()
                    if this_hash.upper().startswith(shard.upper()):
                        logger.info(
                            "Adding Host {} from Shard.".format(roster_id))
                        sharded_roster[roster_id] = roster_args
                    else:
                        logger.debug(
                            "Ignoring Host {} from Shard.".format(roster_id))

                roster = sharded_roster
            else:
                logger.debug("Sharded Roster Not Requested.")

        finally:
            if isinstance(regex, str):
                for roster_id, roster_args in roster.items():
                    if re.match(regex, roster_id):
                        logger.info(
                            "Adding {} on Regex Match".format(roster_id))
                        final_roster[roster_id] = roster_args
                    else:
                        logger.debug(
                            "Ignoring {} No Regex Match".format(roster_id))
            else:
                final_roster = roster

    return final_roster


def dequeue_hosts(thread_num, host_queue, result_queue, this_configs):
    '''
    Pull Data off of the Queue and Collect for that Particular Host
    '''

    logger = logging.getLogger("schedule3.py:dequeue_hosts")

    while host_queue.empty() == False:

        # Store Results Set Failure By Default
        this_status = [False, True, False]

        try:
            roster_id, roster_args = host_queue.get(timeout=3)

            logger.debug("{} Pulled Host {} in thread {}{}".format(Fore.GREEN,
                                                                   roster_id,
                                                                   thread_num,
                                                                   Style.RESET_ALL))

        except Exception as pull_error:

            logger.warning("{}Could not pull host of queue in thread {} with Error.{}".format(Fore.RED,
                                                                                              thread_num,
                                                                                              Style.RESET_ALL))
            logger.debug("Error : {}".format(pull_error))

            roster_id = "unknown"

        else:

            roster_key_ban = ["user", "host", "sudo"]

            this_host_args = dict()

            for item, value in roster_args.items():
                if item not in roster_key_ban:
                    this_host_args[item] = value

            collection_args = {"remote": True,
                               "salt_ssh_basedir": this_configs["schedule"]["salt_ssh_basedir"],
                               "remote_host_id": roster_id,
                               "remote_timeout": this_configs["schedule"].get("indv_call_timeout", 600),
                               "noupload": True,
                               "host_configs": this_host_args,
                               "ipintel_configs": {"dointel": True},
                               "sapi_configs": {"sapi_do_api": False},
                               "hardcrash": False,
                               "base_config_file": this_configs["schedule"]["collection_config_file"],
                               "local_cols": [this_configs["schedule"].get("local_collections", False),
                                              this_configs["schedule"].get("local_collections_location", "/etc/manowar_agent/collections.d")],
                               "relative_venv": this_configs["schedule"].get("relative_venv", False)
                               }

            logger.debug("Collection Arguments : {}".format(collection_args))

            this_host = saltcell.clientcollector.Host(**collection_args)

            try:
                this_store_stats = storage(this_configs,
                                           this_host.todict())

            except Exception as storage_error:
                logger.error(
                    "Unable to Store Collected Items for {}".format(roster_id))
                this_status[1] = True
            else:
                logger.debug("Stored Results for {}".format(roster_id))

                this_status[0] = True

            if roster_args.get("status", "unknown") in ("prod", "mxhot", "mxcold"):
                this_status[2] = True

        finally:

            try:
                logger.info("Placing Result on Queue for {}".format(roster_id))
                logger.debug("Result : {}".format(this_status))

                result_queue.put([roster_id, *this_status])
                logger.debug("{} Placed {} on Result Queue{}".format(
                    Fore.GREEN, roster_id, Style.RESET_ALL))

            except Exception as placement_error:

                logger.error("{}Unable to Place Result on Queue for Host : {}{}".format(
                    Fore.RED, roster_id, Style.RESET_ALL))
                logger.debug("Error : {}".format(placement_error))

    logger.info("{}Queue Empty breaking thread loop {}{}".format(
        Style.DIM, thread_num, Style.RESET_ALL))

    return


def schedule(config_items, regex=None, shard=None, do_print=False):
    '''
    Schedule UP all My Tasks on THe Queue
    '''

    logger = logging.getLogger("schedule3.py:schedule")

    schedule_stats = dict()

    # Counters for Results
    glbl_success_hosts = list()
    glbl_fail_hosts = list()
    glbl_fail_hosts_prod = list()
    sapi_hosts_list = list()

    THREADS = int(config_items["schedule"]["max_threads"])
    schedule_stats["threads"] = THREADS

    MAXRUNTIME = int(config_items["schedule"]["max_runtime"])

    output_report = config_items["schedule"]["output_report"],

    if isinstance(output_report, str):
        json_out = (True, output_report)
    else:
        json_out = (False, "/dev/null")

    active_hosts = read_hosts(config_items, regex=regex)

    # Create my Manager Object
    manager = multiprocessing.Manager()

    # Create a Queue for our hosts to live in.
    host_queue = manager.Queue(maxsize=len(active_hosts.keys())+1)

    # Results Queue
    result_queue = manager.Queue(maxsize=len(active_hosts.keys())+1)

    # Record When Enqueing Started
    start = time.time()

    sapi_hosts_list = list()

    found_sapi_hosts = manoward.grab_all_sapi(config_items)

    logger.info("Found {} Sapi Hosts to ignore".format(len(found_sapi_hosts)))

    # Toss Host on Queue
    for rosterid, host_arguments in active_hosts.items():

        # Check if Host is a SAPI host

        if rosterid in found_sapi_hosts:
            sapi_hosts_list.append(rosterid)
            logger.debug("{} Host {} is a recent SAPI Host, not placing on Queue.{}".format(
                Style.DIM, rosterid, Style.RESET_ALL))
        elif host_arguments.get("resource", None) is not None and host_arguments.get("resource") in found_sapi_hosts:
            sapi_hosts_list.append(rosterid)
            logger.debug("{} Host {} is a recent SAPI Host, not placing on Queue.{}".format(
                Style.DIM, rosterid, Style.RESET_ALL))
        elif host_arguments.get("hostname", None) is not None and host_arguments.get("hostname") in found_sapi_hosts:
            sapi_hosts_list.append(rosterid)
            logger.debug("{} Host {} is a recent SAPI Host, not placing on Queue.{}".format(
                Style.DIM, rosterid, Style.RESET_ALL))
        else:
            host_queue.put([rosterid, host_arguments])

    # Allows muliprocess queue to settle
    logger.debug("Sleeping 5 Seconds for Saftey.")

    time.sleep(5)

    thread_array = dict()

    # Take Hosts Off Queue
    for thread_num in range(THREADS):
        # Set THread Target Always pass it our config_array
        if host_queue.empty() == False:

            logger.debug("{} Provisining Thread Number : {} {}".format(Style.DIM,
                                                                       thread_num,
                                                                       Style.RESET_ALL))

            try:
                thread_array[thread_num] = multiprocessing.Process(target=dequeue_hosts,
                                                                   args=(thread_num,
                                                                         host_queue,
                                                                         result_queue,
                                                                         config_items)
                                                                   )

                # Make Threads Die if Parent is Killed
                thread_array[thread_num].daemon = True
                # Start my Threads
                thread_array[thread_num].start()

            except Exception as thread_init_error:  # pylint: disable=broad-except, invalid-name
                logger.error("Unable to start up thread {} of {}".format(
                    thread_num, THREADS))
                logger.debug("Error : {}".format(thread_init_error))
            finally:

                # I know this is janky. But I've found that it's neccessary to keep weird things
                # Happening with too many threads hitting the queue simultaneously.
                if thread_num < 50:
                    # Always sleep for first 50 threads
                    time.sleep(1)
                elif thread_num % 7 == 0:
                    # Do new threads 7 at a time
                    time.sleep(1)

        else:

            logger.warning("{} Queue is Emptpy Prior to Allocation of All threads. Prematurely stopping allocation. {}".format(
                Style.DIM, Style.RESET_ALL))
            logger.debug("Allocation Stopping At {} Threads out of Planned {}".format(
                thread_num, THREADS))
            break

    logger.info("{} {} {} Thread Allocation Complete.{}".format(Style.DIM,
                                                                Fore.MAGENTA,
                                                                Back.CYAN,
                                                                Style.RESET_ALL))

    # Wait until Unfinished Tasks is less than 10
    current_check_iteration = 0

    while True:
        # Check if were past our timeout
        current_run_time = time.time() - start
        if current_run_time < MAXRUNTIME:
            current_check_iteration += 1
            if (current_check_iteration % 250) == 0:
                FULL_PRINT = True
                logger.debug("On Iteration {} Printing PID List.".format(
                    current_check_iteration))
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
                    if FULL_PRINT:
                        logger.debug("Thread {} Still Running with pid {}".format(thread,
                                                                                  thread_array[thread].pid))

                else:
                    # Can Print Finished Threads
                    threads_finished += 1
                    pass

            # Always VERBOSE Print
            if FULL_PRINT:

                logger.debug("Stats at Time : {}".format(current_run_time))
                logger.debug("Running Threads : {}".format(threads_running))
                logger.debug("Finished Threads : {}".format(threads_finished))
                logger.debug("Hosts Left : {}".format(host_queue.qsize()))
                logger.debug("Results Recieved : {}".format(result_queue.qsize()))

            if any_threads_alive == False:
                # Break While Loop
                break
            # I have running threads keep chugging along

        else:

            # Timeout Has Been Reached
            schedule_stats["Timeout"] = "Timeout reached at {} seconds with {} items left on the queue".format(current_run_time,
                                                                                                               host_queue.qsize())

            logger.warning("TIMEOUT: {}".format(schedule_stats["Timeout"]))

            break

        # If I'm still going, Let's wait 20 seconds before checking again.
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
        except Exception as get_error:
            # Modify Failure Adjustment
            failure_adjustment += 1
            logger.error("{} Error grabbing results Adusting Failure Results.{}".format(Fore.RED,
                                                                                        Style.RESET_ALL))

            logger.debug("Get Error : {}".format(get_error))

        else:
            # List Format for Results
            logger.debug("This Result : {}".format(this_result))
            this_one_host_array = this_result[0]
            success = this_result[1]
            fail = this_result[2]
            fail_prod = this_result[3]

            if success:
                glbl_success_hosts.append(this_one_host_array)
            elif fail:
                glbl_fail_hosts.append(this_one_host_array)
            if fail_prod:
                glbl_fail_hosts_prod.append(this_one_host_array)
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

    output_filename = config_items["schedule"].get("output_report", False)

    if isinstance(output_filename, str) is True:
        logger.debug(
            "Writing Output File Report to {}".format(output_filename))

        with open(output_filename, 'w') as json_out_file:
            json_out_file.write(json.dumps(schedule_stats, indent=4))
    else:
        logger.info("Output File Write Not Requested.")

    return schedule_stats


if __name__ == "__main__":
    schedule(CONFIG, regex=args.regex, shard=args.shard, do_print=args.print)
