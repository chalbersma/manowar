#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# Run through Analysis
import os
import ast
import argparse
from configparser import ConfigParser
import pprint
import pymysql
import json
import re
import packaging.version
from copy import deepcopy
from time import time
from time import sleep
import logging
import sys
import threading
import multiprocessing
# Yes I use both!
from queue import Queue

import yaml

# Analyze Specific
from generic_large_compare import generic_large_compare
from generic_large_analysis_store import generic_large_analysis_store
from subtype_large_compare import subtype_large_compare

import audittools
import db_helper


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--auditdir", help="Directory that Contains the audits", required=False, action='append')
    parser.add_argument("-c", "--config", help="Main analyze.ini file", required=False, default=False)
    parser.add_argument("-v", "--verbose", action='append_const', help="Turn on Verbosity", const=1, default=[])

    parser._optionals.title = "DESCRIPTION "

    # Parser Args
    args = parser.parse_args()

    CONFIGDIR = list()
    # Massage Configdir to not include trailing /
    for thisdir in args.auditdir :
        # Removing Trailing /
        if thisdir[-1] == "/" :
            CONFIGDIR.append(thisdir[0:-1])
        else :
            CONFIGDIR.append(thisdir)

    if list(CONFIGDIR) == 0:
        for this_path in ["/etc/manowar/audits.d", "./etc/manowar/audits.d"]:
            if os.isdir(this_path) is True:
                CONFIGDIR.append(this_path)

    VERBOSE = len(args.verbose)

    if VERBOSE == 0:
        logging.basicConfig(level=logging.ERROR)
    elif VERBOSE == 1:
        logging.basicConfig(level=logging.WARNING)
    elif VERBOSE == 2:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)

    LOGGER = logging.getLogger("analyze.py")

    CONFIG = db_helper.get_manoward(explicit_config=args.config,
                                    only_file=False)

def analyze(CONFIGDIR, CONFIG):

    # Init apt system
    #apt_pkg.init_system()

    logger = logging.getLogger("analyze.py:analyze")

    ANALYZE_TIME = int(time())

    # Parse my General Configuration
    if isinstance(CONFIG, dict):
        config_items = CONFIG
    elif isinstance(CONFIG, str):
        config_items = db_helper.get_manoward(explicit_config=CONFIG)
    else:
        raise TypeError("No Configuration Given.")


    logger.debug("Configuration Items: {}".format(config_items))


    if isinstance(CONFIGDIR, dict):
        loggger.debug("CONFIGDIR is given from external process.")
        audits = CONFIGDIR
    elif isinstance(CONFIGDIR, list):
        # Grab all my Audits in CONFIGDIR Stuff
        auditfiles = audittools.walk_auditd_dir(CONFIGDIR)

        # Read all my Audits
        audits = dict()
        for auditfile in auditfiles :

            these_audits = audittools.load_auditfile(auditfile)

            for found_audit_name in these_audits.keys():
                if found_audit_name in audits.keys():
                    logger.warning("Duplicate definition for {} found. Ignoring definition in file {}".format(found_audit_name, auditfile))
                else:
                    # Add that audit
                    audits[found_audit_name] = these_audits[found_audit_name]


    '''
    def null_or_value(data_to_check):
        # TODO Remove this Eventually
        if data_to_check == None :
            data = "NULL"
            return data
        else :
            data = "'" + str(data_to_check) + "'"
            return data
    '''

    def grab_host_list(db_conn, FRESH=172800):
        # Grab a Host List

        logger = logging.getLogger("grab_host_list")

        db_cur = db_conn.cursor(pymysql.cursors.DictCursor)

        host_query = '''select host_id, pop, srvtype, last_update
                        from hosts
                        where last_update >= now() - INTERVAL %s SECOND'''

        host_query_args = [FRESH]

        try:
            host_list_debug_query = db_cur.mogrify(host_query, host_query_args)
            logger.debug("hostslist Query : {}".format(host_list_debug_query))
            db_cur.execute(host_query, host_query_args)
        except Exception as hlq_error:
            logger.error("Unable to Query for Hostslist.")
            all_hosts = list()
            amount_of_hosts = 0
            host_good = False
        else:
            all_hosts = db_cur.fetchall()

            amount_of_hosts = len(all_hosts)

            if amount_of_hosts > 0 :
                host_good = True
            else :
                host_good = False
        finally:
            db_cur.close()

        return host_good, amount_of_hosts, all_hosts

    '''
    # Match Type, Collection Type, Collection Subtype, MValue
    def generic_compare(db_conn, host_id, mtype, ctype, csubtype, mvalue, FRESH):
        # TODO Can remove?

        cur = db_conn.cursor()

        comparison = []
        comparison.append(" select collection_value from collection where")
        comparison.append(" fk_host_id = '" + str(host_id) + "' ")
        comparison.append(" AND collection_type = '" + ctype + "' ")
        comparison.append(" AND collection_subtype = '" + csubtype + "' ")
        comparison.append(" AND last_update <= now() + INTERVAL " + str(FRESH) + " SECOND ")
        comparison.append(" order by last_update desc limit 1; ")
        comparison_query = " ".join(comparison)

        #print(comparison_query)
        cur.execute(comparison_query)

        if not cur.rowcount :
            # No Results
            this_collected_value = ""
            #print("no_result")
        else :
            this_collected_value_raw = cur.fetchone()[0]
            this_collected_value = null_or_value(this_collected_value_raw)[1:-1]
            #print(this_collected_value)
        # Pass Fail or Exempt
        pfe_value = ""

        if len(this_collected_value) <= 0 :
            # No Results This one is Exempt
            pfe_value = "exempt"
        else :
            # Results to Compare it
            # is = collection in ( string | [ list ] )
            if   mtype == "is" or mtype == "aptis" :
                if this_collected_value in mvalue :
                    # Passed
                    pfe_value = "pass"
                else:
                    pfe_value = "fail"
            # match = re.search ( regexstring, collection )
            elif mtype == "match" or mtype == "atpmatch" :
                if re.search(mvalue, this_collected_value) != None :
                    pfe_value = "pass"
                else :
                    pfe_value = "fail"

            # nematch = re.sarch (regexstring, collection )
            elif mtype == "nematch" :
                if re.search(mvalue, this_collected_value) == None :
                    pfe_value = "pass"
                else :
                    pfe_value = "fail"

            elif mtype == "aptge" or mtype == "verge" :

                collected_version = packaging.version.parse(this_collected_value)
                match_version = packaging.version.parse(mvalue)
                if collected_version >= match_version:
                    # If it's Less than Zero
                    pfe_value = "pass"
                else :
                    pfe_value = "fail"

            # Greater Than
            elif mtype == "gt" :
                if this_collected_value > mvalue :
                    pfe_value = "pass"
                else :
                    pfe_value = "fail"

            # Less Than
            elif mtype == "lt" :
                if this_collected_value < lt :
                    pfe_value = "pass"
            elif mtype == "eq" :
                pfe_value = "exempt"
            else :
                pfe_value = "exempt"

        cur.close()
        return pfe_value, this_collected_value
    '''

    '''
    def subtype_compare(db_conn, host_id, mtype, ctype, csubtype, mvalue, FRESH) :
        # TODO Can Remove?

        # mtype needs to be "subnonhere", "suballhere", "subknowall"
        # csubtype Needs to be an array of subtypes.
        # mvalue any || regex match. If it equals "any" it will not compare.
            # Any other string will match the regext
            # Can add specific matches for different subtypes

        # In order for each one. Rehydrate string (with ") and then convert to a tuple
        interm_processed_csubtype = ast.literal_eval('"' + csubtype.replace("," , "\",\"") + '"')
        interm_processed_mvalue = ast.literal_eval('"' + mvalue.replace("," , "\",\"") + '"')

        # Hydrate a single item into a tuple
        if type(interm_processed_csubtype) is str :
            processed_csubtype = ( interm_processed_csubtype, )
        else :
            processed_csubtype = interm_processed_csubtype

        if type(interm_processed_mvalue) is str:
            processed_mvalue = ( interm_processed_mvalue, )
        else :
            processed_mvalue =  interm_processed_mvalue

        # Create New Cursor
        cur = db_conn.cursor()

        # Debug
        #print(type(mtype))
        #print(mtype)
        #print(type(ctype))
        #print(ctype)
        #print(type(processed_csubtype))
        #print(processed_csubtype)
        #print(type(processed_mvalue))
        #print(processed_mvalue)


        # Give me all the collection_subtypes (and their values) for the given host_id, mtyp, ctype.
        comparison = []
        comparison.append(" select collection_subtype, collection_value from collection where ")
        comparison.append(" fk_host_id = 6 ")
        comparison.append(" and collection_type = '" + ctype +  "' ")
        comparison.append(" and last_update >= now() - INTERVAL 480000 SECOND ")
        comparison.append(" GROUP BY(collection_subtype) ")
        collection_query = " ".join(comparison)

        cur.execute(collection_query)

        pfe_value = "exempt"
        comparison_result = "testing"

        # If I haven't got anything
        if not cur.rowcount :
            # No Results
            no_subtypes = True
        # I've got stuff.
        else :
            no_subtypes = False
            these_subtypes = cur.fetchall()
            # Debug
            #print(type(these_subtypes))
            #print(these_subtypes)
            collected_subtype_list = list()
            collected_value_list = list()
            for row in these_subtypes :
                collected_subtype_list.append(row[0])
                collected_value_list.append(row[1])

            #print(collected_subtype_list)
            #print(collected_value_list)

        if mtype == "subnonhere" :
            # There's none here if there's no subtypes
            #print("subnonhere")
            if no_subtypes == True :
                #print("no Subtypes")
                # We're okay
                pfe_value = "pass"
                comparison_result = "No Collected Subtypes"
            else :
                confirm_fails = []
                # We Got Subtype
                # Do a list-comprehensions Comparison : https://docs.python.org/3/tutorial/datastructures.html#list-comprehensions

                failsubtypes = [ fail for fail in processed_csubtype if fail in collected_subtype_list ]

                # Now I have a failsubtpes list that I can work with

                #print("Fail Values")
                #print(type(failValues))
                #print(failValues)

                # Cycle through Subtype Matches
                for this_subtype_failure in failsubtypes:
                    this_mvalue_index = processed_csubtype.index(this_subtype_failure)
                    #print("My MValue Index")
                    #print(this_mvalue_index)
                    #print("My Match Value")
                    #print(processed_mvalue[this_mvalue_index])
                    if processed_mvalue[this_mvalue_index] == "any" :
                        # Then Leave it Bro it's bad
                        confirm_fails.append(this_subtype_failure)
                    else :
                        # It's something. Find out the index for this value in the collected Value
                        this_collected_value_index = collected_subtype_list.index(this_subtype_failure)
                        # Utilize my indices to do my comparisons
                        # If the value in my indce matches then it's bad. If not It's okay
                        if re.search(processed_mvalue[this_mvalue_index], collected_value_list[this_collected_value_index]) != None :
                            # means there's something there so it fails
                            confirm_fails.append(this_subtype_failure)
                        # If it doesn't match don't add to confirm failures. Instead continue on

                if len(confirm_fails) > 0 :
                    # There's a Confirmed Failure
                    pfe_value = "fail"
                    comparison_result = "Bad Items: " + " ".join(confirm_fails)
                else :
                    pfe_value = "pass"
                    comparison_result = "No Bad Items"


        elif mtype == "suballhere" :
            # There's none that match if there's no subtypes
            if no_subtypes == True :
                # We Bad
                pfe_value = "fail"
                comparison_result = "Unfound: " + csubtype
            else :
                # Grab a list of all the subtypes in our comparison that are not in the collected_subtype_list
                missingsubtypes = [ fail for fail in processed_csubtype if fail not in collected_subtype_list ]

                #print("Debug: Missing Subtypes")
                #print(missingsubtypes)
                # If there's one missing (no matter what) Call it a failure
                if len(missingsubtypes) > 0 :
                    pfe_value = "fail"
                    comparison_result = "Missing Subtypes: " + " ".join(missingsubtypes)
                else :
                    # No Missing Subtypes. Let's go through the collected itmes and see if we have matches.
                    matchfailure = False
                    matchfailures = []
                    for this_csubtype in processed_csubtype :
                        # Grab the index of the match value given with the audit
                        this_mvalue_index = processed_csubtype.index(this_csubtype)
                        #print("Debug: Checking Match " + this_csubtype + " Item Number : " + str(this_mvalue_index))
                        if processed_mvalue[this_mvalue_index] == "any" :
                            # Then This always Succeeds. matchfailure remains False. No additions to matchfailures
                            continue
                        else :
                            # Give the index of the collected value queried from the server
                            this_collected_value_index = collected_subtype_list.index(this_csubtype)

                            #print("DEBUG: ")
                            #print("Do a Comparison")
                            #print(processed_mvalue[this_mvalue_index])
                            #print("Compared To")
                            #print(collected_value_list[this_collected_value_index])
                            #result = re.search(processed_mvalue[this_mvalue_index], collected_value_list[this_collected_value_index])
                            #print(type(result))
                            #print(result)

                            # If the item matches that means it's okay. If not that's a failure
                            if re.search(processed_mvalue[this_mvalue_index], collected_value_list[this_collected_value_index]) == None :
                                # When it's none that means there's no match. So Append this to failure
                                matchfailure = True
                                matchfailures.append(this_csubtype)

                    # Loop Ends

                    #print("DEBUG Matchfailure")
                    #print(matchfailure)
                    #print(matchfailures)
                    if matchfailure == False :
                        # No Match Failures. All our Items are there. We've passed
                        pfe_value = "pass"
                        comparison_result = "All Items Matched."
                    else :
                        # Match Failure is True
                        pfe_value = "fail"
                        comparison_result = "MValue Mismatch: " + " ".join(matchfailures)


        elif mtype == "subknowall" :
            #print("Debug: Subknowall")
            # No Subtypes so I can't match all known either.
            if no_subtypes == True :
                # We still bad
                pfe_values = "pass"
                comparison_result = "No Subtypes"
            else :
                # Subtypes Here!
                unaccounted_for_subtypes = [ subtype for subtype in collected_subtype_list if subtype not in processed_csubtype ]

                if len(unaccounted_for_subtypes) > 0 :
                    # There's an unaccounted for Subtype so Fail.
                    pfe_value = "fail"
                    comparison_result = "Unknown Subtypes: " + " ".join(unaccounted_for_subtypes)
                else :
                    matchfailure = False
                    matchfailures = []
                    for this_collected_subtype in collected_subtype_list :
                        # Go through each item in the subtype and make sure that it's okay
                        # Find the index of the item in the database in the audit
                        this_mvalue_index = processed_csubtype.index(this_collected_subtype)
                        if processed_mvalue[this_mvalue_index] == "any" :
                            # Any value is okay so mark it as okay
                            continue
                        else :
                            # I need to do a comparision So I need to grab the collected value for the subtype in question
                            # To do that I need to look up it's index
                            this_collected_value_index = collected_subtype_list.index(this_collected_subtype)

                            # Regex Search for my Item
                            if re.search(processed_mvalue[this_mvalue_index], collected_value_list[this_collected_value_index]) == None :
                                # If there's no match then call it false
                                matchfailure = True
                                matchfailures.append(this_collected_subtype)

                    # End of Loop
                    if matchfailure == False :
                        # No Match Failures
                        pfe_value = "pass"
                        comparison_result = "All Items Known"
                    else :
                        # Match Failure is True
                        pfe_value = "fail"
                        comparison_result = "MValue Mismatch: " + " ".join(matchfailures)


        # print("Debug", pfe_value, comparison_result)
        return pfe_value, comparison_result
    '''


    def analyze_one_audit(db_config_items, list_of_hosts, oneAudit, auditName, return_dict, audit_id) :

        # Note that db config items is the same as config_itesm

        logger = logging.getLogger("analyze_one_audit")

        try:
            # I multithread like a boss now. :) JK But I need to give each audit it's own conn to the DB:
            db_conn = db_helper.get_conn(db_config_items, prefix="analyze_", tojq=".database", ac_def=True)

            #
            host_buckets = dict()
            host_comparison = dict()


            # New Results Variables for Future Reference
            pop_results = dict()
            srvtype_results = dict()
            audit_results = dict()

            # Add Insert_Update Counters
            audit_host_inserts = 0
            audit_host_updates = 0

            # Debug Host No More

            # Create Bucket Objects from Config
            for bucket in oneAudit["filters"] :
                host_buckets[bucket] = []
                host_comparison[bucket] = []

            # Bucket Hosts Left (All the hosts before I start silly
            items_left_to_bucket = list_of_hosts

            for bucket in oneAudit["filters"] :

                this_mtype = oneAudit["filters"][bucket]["filter-match"]
                this_ctype = oneAudit["filters"][bucket]["filter-collection-type"]
                this_csubtype = oneAudit["filters"][bucket]["filter-collection-subtype"]
                this_mvalue = oneAudit["filters"][bucket]["filter-match-value"]


                #print(this_mtype, this_ctype, this_csubtype, this_mvalue)
                try:
                    bucket_results = generic_large_compare(db_conn, items_left_to_bucket, this_mtype, this_ctype, this_csubtype, this_mvalue, FRESH, exemptfail=True)
                except Exception as glc_bucket_results_error:
                    logger.error("Error on Generic Large Compare on bucket {} : audit {}".format(bucket, auditName))
                    logger.warning("Maybe no Hosts for Bucket {} on audit {}".format(bucket, auditName))
                    logger.debug("Error : {}".format(glc_bucket_results_error))
                else:
                    # Grab just the items that passed
                    for result in bucket_results :
                        if "pfe" in result.keys() :
                            if result["pfe"] == "pass" :
                                # Remove pfe & pfevalue from this host so it can be checked again
                                try:
                                    del result["pfe"]
                                    del result["pfevalue"]
                                    # Add my stripped result to the host bucket.
                                    #print(result)
                                    host_buckets[bucket].append(result)
                                except Exception as e:
                                    print("Error adding host to host buckets" , e )

                    # Make an index of just the host ids
                    this_bucket_ids = [ gotem["host_id"] for gotem in host_buckets[bucket] ]

                    # Grab just the items that haven't been bucketd yet (so I don't have to compare everything, everytime)
                    items_left_to_bucket = [ host_id for host_id in list_of_hosts if host_id not in this_bucket_ids ]


            # Host Bucketing
            for comparison in host_buckets.keys() :
                #print(comparison)
                try:
                    this_mtype = oneAudit["comparisons"][comparison]["comparison-match"]
                    this_ctype = oneAudit["comparisons"][comparison]["comparison-collection-type"]
                    this_csubtype = oneAudit["comparisons"][comparison]["comparison-collection-subtype"]
                    this_mvalue = oneAudit["comparisons"][comparison]["comparison-match-value"]
                    #print(this_mtype, this_ctype, this_csubtype, this_mvalue)
                except Exception as comparison_error:
                    logger.error("Error grabbing comparisons for audit {} : {}".format(auditName, comparison_error))
                else:
                    # Check What Type
                    if this_mtype in ["subnonhere", "suballhere", "subknowall"] :
                        # Add Massive Subtype
                        try:
                            comparison_results = subtype_large_compare(db_conn, host_buckets[comparison], this_mtype, this_ctype, this_csubtype, this_mvalue, FRESH)
                        except Exception as subtype_large_compare_error:
                            logger.error("{} Error on Subtype Large Compare on Comparison for bucket {}".format(auditName,
                                                                                                                comparison))

                            logger.debug("Error : {}".format(subtype_large_compare_error))
                        else:
                            host_comparison[comparison] = comparison_results

                    else:
                        # Generic Comparison
                        try:
                            comparison_results = generic_large_compare(db_conn, host_buckets[comparison], this_mtype, this_ctype, this_csubtype, this_mvalue, FRESH)
                            #print(comparison_results)
                        except Exception as generic_large_compare_error:
                            logger.error("{} Error on Generic Large Compare on Comparison for bucket {}".format(auditName,
                                                                                                                comparison))

                            logger.debug("Error : {}".format(generic_large_compare_error))
                        else:
                            host_comparison[comparison] = comparison_results

            #bucket in host_bucket
            #print(auditName, " Results : ", host_comparison)
            massinserts = 0
            massupdates = 0
            massinserts, massupdates = generic_large_analysis_store(db_conn, audit_id, host_comparison, FRESH)


            # Return Dict is a manager.dict() so the "above" process knows what changes here.
            return_dict["host_inserts"]  = massinserts
            return_dict["host_updates"] = massupdates

        except Exception as analyze_error:
            logger.error("Error doing analyze for {} : {}".format(auditName, analyze_error))
            exit(1)
        else:
            exit(0)



    def dequeue_hosts(db_config_items, list_of_hosts):

        logger = logging.getLogger("analyze:dequeue_hosts")

        while True:
            # Pull Stats Stuff
            # Pull Enqueued Host
            global audit_host_inserts
            global audit_host_updates
            #global srvtype_results
            #global pop_results
            #global audit_results

            #print(audit_results)

            try:
                oneAudit, auditName = audit_queue.get()
            except Exception as audit_get_error:
                logger.error("Failure to Pull Items off of Queue.")
                logger.debug("Error : {}".format(audit_get_error))

                audit_queue.task_done()

                # Abnormal Return
                return

            try:
                manager = multiprocessing.Manager()
            except Exception as multiprocess_error:
                logger.error("Failure to Create Manager for audit {} with error {}".format(auditName,
                                                                                            multiprocess_error))
                audit_queue.task_done()

                # Abnormal Return
                return
            else:
                return_dict = manager.dict()

            # Insert Update the Audit in the Database
            try:
                audit_id = insert_update_audit(db_config_items, oneAudit)
            except Exception as update_audit_db_error:
                logger.error("Failure to Create Audit {} in DB with error {}".format(auditName, update_audit_db_error))
                audit_queue.task_done()
                return
            else:
                oneAudit["audit_id"] = audit_id
                logger.debug("Stored a Record about audit {}/{} in the database.".format(auditName, audit_id))

            #print("Pulled Host ", this_one_host_array)
            # Process One Host Pass it the host_array and the config_array
            try:
                #analyze_one_audit(db_config_items, list_of_hosts, oneAudit, auditName, return_dict, audit_id)
                # analyze_audit_process is a new instance for every new thread we make.
                try:
                    analyze_audit_process = multiprocessing.Process(target=analyze_one_audit, args=(db_config_items, list_of_hosts, oneAudit, auditName, return_dict, audit_id))
                    analyze_audit_process.name = auditName
                    analyze_audit_process.daemon = True
                    analyze_audit_process.start()
                except Exception as analyze_pid_error:
                    logger.error("Error with Analyze Audit {} : {}".format(auditName, analyze_pid_error))

                    analyze_audit_process.terminate()
                else:

                    while multiprocessing.Process.is_alive(analyze_audit_process) == True :
                        logger.debug("Waiting for: {} {}".format(auditName, multiprocessing.Process.is_alive(analyze_audit_process)))

                        # Waith 45 Seconds before Asking again
                        sleep(45)

                    analyze_audit_process.join()

            except Exception as audit_analyisis_error:
                logger.error("Failure to Analyze Audit {} : {}".format(auditName,
                                                                       audit_analyisis_error))

            # I/U Stats only Thing Left
            logger.debug(return_dict)
            try:
                with audit_host_counts_lock :
                    logger.info("{} I:{} U:{}".format(auditName,
                                                      return_dict["host_inserts"],
                                                      return_dict["host_updates"]))

                    # This is a Global
                    audit_host_inserts += return_dict["host_inserts"]
                    audit_host_updates += return_dict["host_updates"]

            except Exception as metrics_error:
                #print(return_dict)
                logger.error("Failure on Audit when Recording Metrics {} : {}".format(auditName,
                                                                                      metrics_error))
            audit_queue.task_done()

        return

    def analyze_all_audits(db_config_items, list_of_hosts, FRESH, MAXTHREADS) :
        # Audits are a global variable
        logger = logging.getLogger("analyze_all_audits")

        # Copy Time
        results_host = deepcopy(list_of_hosts)

        # Create My ThreadPool
        for x  in range(MAXTHREADS):
            # This is the magic. It calls dequeu hostsk
            t  = threading.Thread(target=dequeue_hosts, args=(db_config_items, list_of_hosts))
            # Make Threads Die if Parent is Killed
            t.daemon = True
            # Start my Threads
            t.start()

        # Counter for Time Spent
        start = time()

        for audit in audits :
            # Populate Audit Queue
            logger.info("About to Queue audit {}".format(audit))
            #try:
            this_queue_item = [audits[audit], audit]
            audit_queue.put(this_queue_item)

            # Sleep to allow for better placement
            sleep(1)


        # If your running verbosely Print out this stuff Else not
        while audit_queue.unfinished_tasks > 0 :

            nowtime = time() - start

            logger.debug("---------------------------------------")
            logger.debug("AuditsLeft : {}".format(audit_queue.unfinished_tasks))
            logger.debug("QSize : {}".format(audit_queue.qsize()))
            logger.debug("Thread : {}".format(threading.active_count()))
            logger.debug("QStuff : {}".format(audit_queue.empty()))
            logger.debug("Time : {}".format(nowtime))
            logger.debug("---------------------------------------")
            # Give me an Update every 30 seconds
            sleep(15)

        # When I'm Not Verbose Just wait and don't say shit.
        # Otherwise when I see a small number of unfinished tasks Let's move back an djoin.
        audit_queue.join()

        jobtime = time() - start

        return audit_host_inserts, audit_host_updates, jobtime

    def insert_update_audit(db_config_items, audit) :

        logger = logging.getLogger("analyze:insert_update_audit")

        # Literals
        this_audit_name = audit["vuln-name"]
        this_audit_short = audit["vuln-short-description"]
        this_audit_long_description = re.sub(r'[\'|\;]',r'',audit["vuln-long-description"][:511])
        this_audit_primary_link = audit["vuln-primary-link"]
        this_audit_secondary_links = audit["vuln-additional-links"]
        this_audit_filters = audit["filters"]
        this_audit_comparison = audit["comparisons"]
        this_audit_filename = audit["filename"]
        this_audit_priority = audit.get("vuln-priority", 5 )

        db_conn = db_helper.get_conn(db_config_items, prefix="analyze_", tojq=".database", ac_def=True)

        cur = db_conn.cursor()

        # Always Match by audit_name
        grab_audit = "SELECT audit_id from audits where audit_name = %s ; "
        grab_audit_paramaters = [ str(this_audit_name) ]



        cur.execute(grab_audit, grab_audit_paramaters)

        if cur.rowcount :
            # There's Data
            this_audit_id = cur.fetchone()[0]
            have_audit_id = True
        else:
            have_audit_id = False

        replace_query_args = list()

        # Always Specified Columns
        columns = """audit_name, audit_short_description, audit_long_description,
                    audit_primary_link, audit_secondary_links, audit_filters,
                    audit_comparison, audit_priority, filename """

        dynamic_column_items = list()
        dynamic_column_args = list()

        #print(this_audit_secondary_links)

        for secondary_link in this_audit_secondary_links :
            #print(secondary_link)
            dynamic_column_items.append(" %s , %s ")

            # Add to Args List
            dynamic_column_args.append(str(secondary_link))
            dynamic_column_args.append(str(this_audit_secondary_links[secondary_link]))

        # Make this a list of double %s 's
        # Put it in the thing
        dynamic_column = " , ".join(dynamic_column_items)
        dynamic_column = "COLUMN_CREATE(" + dynamic_column + ")"

        # Values String
        this_audit_values = " %s , %s , %s , %s , " + dynamic_column + ", %s " + \
                             " , %s , %s , %s "


        this_audit_value_paramaters=[ str(this_audit_name), str(this_audit_short)[:63], str(this_audit_long_description), str(this_audit_primary_link) ]
        this_audit_value_paramaters.extend(dynamic_column_args)


        temp_list = [ str(this_audit_filters).replace('\'', '"')[:511] , str(this_audit_comparison).replace('\'', '"')[:511] , \
                        str(this_audit_priority) , str(this_audit_filename) ]

        this_audit_value_paramaters.extend(temp_list)

        query_head = "REPLACE into audits ( "
        query_mid = " ) VALUES ( "

        query_tail = " ) "


        if have_audit_id :
            # Have Audit ID so add it, otherwise these won't be added
            columns = columns + " , audit_id "
            this_audit_values = this_audit_values + ", %s "
            this_audit_value_paramaters.append(str(this_audit_id))

        query_string = query_head + columns + query_mid + this_audit_values + query_tail

        # This is a replace and will update the audit no matter.
        debug_sql = cur.mogrify(query_string, this_audit_value_paramaters)
        cur.execute(query_string, this_audit_value_paramaters)

        this_row = cur.lastrowid

        cur.close()
        return this_row

    # Globals
    global pop_results
    global srvtype_results
    global audit_results
    # Inserts Updates
    global audit_host_inserts
    global audit_host_updates


    # Results dictionaries
    pop_results = dict()
    pop_results_lock = threading.Lock()
    srvtype_results = dict()
    srvtype_results_lock = threading.Lock()
    audit_results = dict()
    audit_results_lock = threading.Lock()

    audit_host_inserts = 0
    audit_host_updates = 0
    audit_host_counts_lock = threading.Lock()

    # COnfig ITems
    MAX = config_items["storage"]["collectionmaxchars"]
    FRESH = config_items["analyze"]["freshseconds"]
    MAXTHREADS = int(config_items["analyze"]["maxthreads"])

    # Create A Queue
    audit_queue = Queue()

    #try:
    try:
        db_conn = db_helper.get_conn(config_items, prefix="analyze_", tojq=".database", ac_def=True)
        dbmessage = "Connected"
    except Exception as db_conn_error:
        dbmessage = "Unable to Connect"
        logger.debug("DB Connection Error : {}".format(db_conn_error))
    finally:
        # Start my analyze_stats with data
        analyze_stats = {"db-status" : dbmessage}

    # Grab Hosts List (Still Single Threaded)
    host_good, analyze_stats["FreshHosts"], host_list = grab_host_list(db_conn, FRESH)

    if host_good :
        logger.info("Successfully Collected {} Hosts as 'Live'".format(len(host_list)))

        analyze_stats["HostCollectionStatus"] = "Success"

        analyze_stats["audit_inserts"], analyze_stats["audit_updates"], analyze_stats["jobtime"] = analyze_all_audits(config_items, host_list, FRESH, MAXTHREADS)

        analyze_stats["threads"] = str(MAXTHREADS)
        analyze_stats["totalaudits"] = len(audits)

    else :
        analyze_stats["HostCollectionStatus"] = "Failed"

    return analyze_stats


if __name__ == "__main__":
    analyze_stats = analyze(CONFIGDIR, CONFIG)

    print(json.dumps(analyze_stats, sort_keys=True, indent=4))
