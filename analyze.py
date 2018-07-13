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
import apt_pkg
from copy import deepcopy
from time import time
from time import sleep

import threading
import multiprocessing
# Yes I use both!
from queue import Queue

# Analyze Specific
from generic_large_compare import generic_large_compare
from generic_large_analysis_store import generic_large_analysis_store
from subtype_large_compare import subtype_large_compare



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-a", "--auditdir", help="Directory that Contains the audits", required=True, action='append')
    parser.add_argument("-c", "--config", help="Main analyze.ini file", required=True)
    parser.add_argument("-V", "--verbose", action='store_true', help="Verbose Mode Show more Stuff")
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

    #
    CONFIG=args.config

    if args.verbose:
        VERBOSE=True
    else:
        VERBOSE=False



def analyze(CONFIGDIR, CONFIG):

    # Init apt system
    apt_pkg.init_system()

    ANALYZE_TIME = int(time())

    # Grab all my Audits in CONFIGDIR Stuff
    auditfiles = []
    for thisconfigdir in CONFIGDIR :
        for (dirpath, dirnames, filenames) in os.walk(thisconfigdir) :
            for singlefile in filenames :
                onefile = dirpath + "/" +  singlefile
                #print(singlefile.find(".ini", -4))
                if singlefile.find(".ini", -4) > 0 :
                    # File ends with .ini Last 4 chars
                    auditfiles.append(onefile)

    # Debug
    print(auditfiles)
    # Config Defaults
    this_time=int(time())
    back_week=this_time-604800
    back_month=this_time-2628000
    back_quarter=this_time-7844000
    back_year=this_time-31540000
    back_3_year=this_time-94610000
    time_defaults={ "now" : str(this_time), "weekago" : str(back_week), "monthago" : str(back_month), "quarterago" : str(back_quarter), "yearago" : str(back_year), "threeyearago" : str(back_3_year) }


    # Parse Information
    try:
        # Read Our INI with our data collection rules
        config = ConfigParser(time_defaults)
        config.read(CONFIG)
        # Debug
        #for i in config :
            #for key in config[i] :
                #print (i, "-", key, ":", config[i][key])
    except Exception as e: # pylint: disable=broad-except, invalid-name
        sys.exit('Bad configuration file {}'.format(e))


    # DB Config Items
    db_config_items=dict()
    for section in config:
        if section in ["database"] :
            for item in config[section]:
                db_config_items[item] = config[section][item]

    # Parse the Dicts
    audits=dict()
    for auditfile in auditfiles :
        try:
            # Try to Parse
            this_audit_config = ConfigParser(time_defaults)
            this_audit_config.read(auditfile)
        except Exception as e:
            # Error if Parse
            print("File ", auditfile, " not paresed because of " , format(e))
        else:
            # It's good so toss that shit in
            for section in this_audit_config :
                if section not in ["GLOBAL", "DEFAULT"] :
                    audits[section] = dict()
                    audits[section]["filename"] = auditfile
                    for item in this_audit_config[section]:
                        onelinethisstuff = "".join(this_audit_config[section][item].splitlines())
                        try:
                           if item == "vuln-long-description" :
                                audits[section][item] = ast.literal_eval("'''{}'''".format(onelinethisstuff))
                           else:
                                audits[section][item] = ast.literal_eval(onelinethisstuff)
                        except Exception as e:
                            print("Verification Failed. Use verifyAudits.py for more details")
                            exit(1)

    # Debug
    #print(audits)

    def null_or_value(data_to_check):
        if data_to_check == None :
            data = "NULL"
            return data
        else :
            data = "'" + str(data_to_check) + "'"
            return data

    def grab_host_list(db_conn, FRESH):

        cur = db_conn.cursor(pymysql.cursors.DictCursor)

        host_query_head = '''select
                                host_id, pop, srvtype, last_update
                             from
                                hosts
                             where
                                last_update >= now() - INTERVAL '''
        host_query_tail = " SECOND;"
        host_query = host_query_head + FRESH + host_query_tail


        cur.execute(host_query)
        all_hosts = cur.fetchall()


        amount_of_hosts = len(all_hosts)

        if amount_of_hosts > 0 :
            host_good = True
        else :
            host_good = False

        cur.close()

        return host_good, amount_of_hosts, all_hosts

    # Match Type, Collection Type, Collection Subtype, MValue
    def generic_compare(db_conn, host_id, mtype, ctype, csubtype, mvalue, FRESH):

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

            # aptge = apt_pkg.version_compare( match, collection )
            elif mtype == "aptge" :
                #print("Aptge_Result")
                #print(apt_pkg.version_compare( this_collected_value, mvalue ))
                if apt_pkg.version_compare(  this_collected_value, mvalue ) < 0 :
                    # If it's Less than Zero
                    pfe_value = "fail"
                else :
                    pfe_value = "pass"

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


    def subtype_compare(db_conn, host_id, mtype, ctype, csubtype, mvalue, FRESH) :

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


    def analyze_one_audit(db_config_items, list_of_hosts, oneAudit, auditName, return_dict, audit_id) :

        try:
            # I multithread like a boss now. :) JK But I need to give each audit it's own conn to the DB:
            db_conn, db_message, analyze_stats = giveMeDB(db_config_items)
            # oneAudit = audits[audit]
            # list_of_hosts = list_of_host
            # pop_results, srvtype_results, audit_result | Need a global lock for updating.

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



                    #print("in bucket", bucket)
                    this_mtype = oneAudit["filters"][bucket]["filter-match"]
                    this_ctype = oneAudit["filters"][bucket]["filter-collection-type"]
                    this_csubtype = oneAudit["filters"][bucket]["filter-collection-subtype"]
                    this_mvalue = oneAudit["filters"][bucket]["filter-match-value"]


                    #print(this_mtype, this_ctype, this_csubtype, this_mvalue)
                    try:
                        bucket_results = generic_large_compare(db_conn, items_left_to_bucket, this_mtype, this_ctype, this_csubtype, this_mvalue, FRESH, exemptfail=True)
                    except Exception as e:
                        print("Error on Generic Large Compare on bucket", bucket, " For audit ", auditName)
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


            #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            #print(host_buckets)
            #print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

            for comparison in host_buckets.keys() :
                #print(comparison)
                try:
                    this_mtype = oneAudit["comparisons"][comparison]["comparison-match"]
                    this_ctype = oneAudit["comparisons"][comparison]["comparison-collection-type"]
                    this_csubtype = oneAudit["comparisons"][comparison]["comparison-collection-subtype"]
                    this_mvalue = oneAudit["comparisons"][comparison]["comparison-match-value"]
                    #print(this_mtype, this_ctype, this_csubtype, this_mvalue)
                except Exception as e:
                    print("Error grabbing comparisons for audit ", auditName, " : " , e)

                # Check What Type
                if this_mtype in [ "subnonhere", "suballhere", "subknowall" ] :
                    # Add Massive Subtype
                    try:
                        comparison_results = subtype_large_compare(db_conn, host_buckets[comparison], this_mtype, this_ctype, this_csubtype, this_mvalue, FRESH)
                    except Exception as e:
                        print("Error on Subtype Large Compare on Comparison for bucket", comparison, " For audit ", auditName, " : ", e)
                else:
                    # Generic Comparison
                    try:
                        comparison_results = generic_large_compare(db_conn, host_buckets[comparison], this_mtype, this_ctype, this_csubtype, this_mvalue, FRESH)
                        #print(comparison_results)
                    except Exception as e:
                        print("Error on Generic Large Compare on Comparison for bucket", comparison, " For audit ", auditName, " : " , e)

                # And Doo it! (But for either collection type
                host_comparison[comparison] = comparison_results

            #bucket in host_bucket
            #print(auditName, " Results : ", host_comparison)
            massinserts = 0
            massupdates = 0
            massinserts, massupdates = generic_large_analysis_store(db_conn, audit_id, host_comparison, FRESH)


            return_dict["host_inserts"]  = massinserts
            return_dict["host_updates"] = massupdates


            #print(return_dict)
            exit(0)
        except Exception as e :
            print("Error doing analyze", e)
            exit(1)


    def dequeue_hosts(db_config_items, list_of_hosts):
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
            except Exception as e:
                print("Failure to Pull Items off of Queue.")
                audit_queue.task_done()
                return

            try:
                manager = multiprocessing.Manager()
            except Exception as e:
                print("Failure to Create Manager for audit ", auditName, " with error: ", e)
                audit_queue.task_done()
                return

            try:
                return_dict = manager.dict()
            except Exception as e:
                print("Failure to Create Return Dictionary for audit ", auditName, " with error: ", e)
                audit_queue.task_done()
                return




            # Insert Update the Audit in the Database
            try:
                audit_id = insert_update_audit(db_config_items, oneAudit)
            except Exception as e:
                print("Failure to Create Audit", auditName, " in Database: ", e)
                audit_queue.task_done()
                return


            #print("Audit ID Successufl", audit_id)

            # Grab My Audit ID and store it for future Reference with oneAudit
            oneAudit["audit_id"] = audit_id

            #print("Pulled Host ", this_one_host_array)
            # Process One Host Pass it the host_array and the config_array
            try :
                #analyze_one_audit(db_config_items, list_of_hosts, oneAudit, auditName, return_dict, audit_id)
                # analyze_audit_process is a new instance for every new thread we make.
                try:
                    analyze_audit_process = multiprocessing.Process(target=analyze_one_audit, args=(db_config_items, list_of_hosts, oneAudit, auditName, return_dict, audit_id))
                    analyze_audit_process.name = auditName
                    analyze_audit_process.daemon = True
                    analyze_audit_process.start()
                except Exception as e:
                    print("Error with Analyze Audit", auditName, " Critical Error: ", e)
                    analyze_audit_process.terminate()

                while multiprocessing.Process.is_alive(analyze_audit_process) == True :
                    if VERBOSE:
                        print("Waiting for: ", auditName, multiprocessing.Process.is_alive(analyze_audit_process) )

                    sleep(30)

                try:
                    analyze_audit_process.join()
                except Exception as e:
                    print("Join Error on Audit: ", auditName, " : ", e)

            except Exception as e:
                print("Failure to Analyze Audit", auditName, " Critical Error: ", e)

            # I/U Stats only Thing Left
            try:
                with audit_host_counts_lock :
                    if VERBOSE:
                        print(auditName, " I/U ", return_dict["host_inserts"], return_dict["host_updates"])

                    audit_host_inserts += return_dict["host_inserts"]
                    audit_host_updates += return_dict["host_updates"]
                    #print("Audit Results", audit_host_inserts, audit_host_updates)
            except Exception as e :
                #print(return_dict)
                print("Failure on Audit ", auditName, " while updating audit counts:", e)
                pass

            # moving srvtype, pop & acoll results to own modules
            '''
            try:
                with srvtype_results_lock :
                    # Add Srvtype Results with Srvtype Lock
                    if len(return_dict["srvtype_results"]) :
                        srvtype_results[audit_id] = return_dict["srvtype_results"]
                        #print("SRVTYPE Results", srvtype_results)
            except Exception as e :
                print("Failure on Audit ", auditName, " while updating srvtype_results:", e)
                pass

            try:
                with pop_results_lock :
                    # POP Results From Multiprocess Process
                    if len(return_dict["pop_results"]) > 0 :
                        pop_results[audit_id] = return_dict["pop_results"]
                        #print(pop_results)
            except Exception as e :
                print("Failure on Audit ", auditName, " while updating pop results:", e)
                pass

            try:
                with audit_results_lock :
                    # Audit Results
                    audit_results[audit_id] = return_dict["audit_results"]
                    #print("Audit Results", audit_results)
            except Exception as e :
                print("Failure on Audit ", auditName, " while updating audit_results:", e)
                #print(return_dict.keys())
                pass
            '''

            # Dequeue the Host from host_queue

            audit_queue.task_done()
        return

    def analyze_all_audits(db_config_items, list_of_hosts, FRESH, MAXTHREADS) :
        # Audits are a global variable

        results_host = deepcopy(list_of_hosts)

        # Create My ThreadPool
        for x  in range(MAXTHREADS):
            t  = threading.Thread(target=dequeue_hosts, args=(db_config_items, list_of_hosts))
            # Make Threads Die if Parent is Killed
            t.daemon = True
            # Start my Threads
            t.start()

        # Counter for Time Spent
        start = time()

        for audit in audits :
            # Essentially Updates Via Reference. Should be Self Contained
            #try:
            this_queue_item = audits[audit], audit
            audit_queue.put( this_queue_item )
            sleep(1)


        # If your running verbosely Print out this stuff Else not
        while audit_queue.unfinished_tasks > 0 :
            if VERBOSE :
                nowtime = time() - start
                print("---------------------------------------")
                print("AuditsLeft \t QSize \t Thread \t QStuff\t Time ")
                print(audit_queue.unfinished_tasks, "\t\t", audit_queue.qsize(), "\t", threading.active_count(), "\t\t", audit_queue.empty(),"\t", nowtime)
                print("---------------------------------------")
                sleep(15)

        # When I'm Not Verbose Just wait and don't say shit.
        audit_queue.join()

        jobtime = time() - start

        return audit_host_inserts, audit_host_updates, jobtime

    '''
    def store_audit_by_host(db_conn, bucket, audit_id, host, result, collected_value):

        #print(host)
        cur = db_conn.cursor()

        # Set Variables
        this_audit_id = audit_id
        this_host_id = host["host_id"]

        if result == "pass" :
            result_enum = "'pass'"
        elif result == "fail" :
            result_enum = "'fail'"
        else :
            # Exempt
            result_enum = "'notafflicted'"

        #print(result, result_enum)

        if collected_value == "" :
            collected_value_store = "NULL"
        else:
            collected_value_store = collected_value

        columns = " fk_host_id, fk_audits_id, initial_audit, last_audit, bucket, audit_result, audit_result_text "
        value   = str(this_host_id) + ", " + str(this_audit_id) + ", " + "FROM_UNIXTIME(" + str(ANALYZE_TIME) + "), " + "FROM_UNIXTIME(" + str(ANALYZE_TIME) + "), '" + bucket + "', " + result_enum + ", '" + collected_value_store + "'"

        #print(columns)
        #print(value)
        #print("Debug Collected_value", collected_value)

        if collected_value == "" :
            # No Value to Compare (For Null Values)
            # Otherwise we insert every notafflicted NULL
            value_compare_string = " "
        else :
            value_compare_string = " and audit_result_text = '" + str(collected_value) + "' "


        # Grab the latest selection
        grab_last_collection_query="SELECT audit_result_id, audit_result from audits_by_host where fk_audits_id = " + str(this_audit_id) + " and fk_host_id = " + str(this_host_id) + " and audit_result = " + result_enum + value_compare_string + " and bucket = '" + bucket + "'  order by last_audit limit 1 ; "

        #print(grab_last_collection_query)

        cur.execute(grab_last_collection_query)

        if cur.rowcount :
            # There's Data so Just Update last_audit
            this_audit_result_id = cur.fetchone()[0]
            #print(this_audit_result_id)
            update_query = "UPDATE audits_by_host SET last_audit = FROM_UNIXTIME(" + str(ANALYZE_TIME) + ") where audit_result_id = '" + str(this_audit_result_id) + "' ; commit ; "
            #print(update_query)
            cur.execute(update_query)
            have_audit_id = True
        else:
            # No Data Do Insert
            have_audit_id = False
            insert_query = "Insert into audits_by_host (" + columns + ") VALUES ( " + value + ") ; commit ;"
            #print(insert_query)
            cur.execute(insert_query)

        if have_audit_id :
            inserts = 0
            updates = 1
        else :
            inserts = 1
            updates = 0

        return inserts, updates

    '''

    def insert_update_audit(db_config_items, audit) :

        #print(audit)

        # Literals
        this_audit_name = audit["vuln-name"]
        this_audit_short = audit["vuln-short-description"]
        this_audit_long_description = re.sub(r'[\'|\;]',r'',audit["vuln-long-description"])
        this_audit_primary_link = audit["vuln-primary-link"]
        this_audit_secondary_links = audit["vuln-additional-links"]
        this_audit_filters = audit["filters"]
        this_audit_comparison = audit["comparisons"]
        this_audit_filename = audit["filename"]
        this_audit_priority = audit.get("vuln-priority", 5 )

        db_conn, dbmessage, analyze_stats = giveMeDB(db_config_items)

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


        this_audit_value_paramaters=[ str(this_audit_name), str(this_audit_short), str(this_audit_long_description), str(this_audit_primary_link) ]
        this_audit_value_paramaters.extend(dynamic_column_args)


        temp_list = [ str(this_audit_filters).replace('\'', '"') , str(this_audit_comparison).replace('\'', '"') , \
                        str(this_audit_priority) , str(this_audit_filename) ]

        this_audit_value_paramaters.extend(temp_list)

        query_head = "REPLACE into audits ( "
        query_mid = " ) VALUES ( "

        query_tail = " ) ; commit; "


        if have_audit_id :
            # Have Audit ID so add it, otherwise these won't be added
            columns = columns + " , audit_id "
            this_audit_values = this_audit_values + ", %s "
            this_audit_value_paramaters.append(str(this_audit_id))

        query_string = query_head + columns + query_mid + this_audit_values + query_tail

        # This is a replace and will update the audit no matter.
        debug_sql = cur.mogrify(query_string, this_audit_value_paramaters)
        print("Debug SQL {}".format(debug_sql))
        try:
            cur.execute(query_string, this_audit_value_paramaters)
        except Exception as msyql_except:
            print("Error Adding Audit: {}".format(str(mysql_except)))
            raise Exception("Unable to Insert Audit")
        else:
            pass

        this_row = cur.lastrowid

        cur.close()
        return this_row

    '''
    def store_sub_results(db_conn, subtable, pop_or_srvtype):


        #print(subtable)
        #print(pop_or_srvtype)


        cur = db_conn.cursor(pymysql.cursors.DictCursor)

        for audit_id in pop_or_srvtype :
            # Cycle Through Audits
            #print(pop_or_srvtype[audit_id])
            for popSrvtype in pop_or_srvtype[audit_id].keys() :
                this_pass = pop_or_srvtype[audit_id][popSrvtype][0]
                this_fail = pop_or_srvtype[audit_id][popSrvtype][1]
                this_exem = pop_or_srvtype[audit_id][popSrvtype][2]
                this_timestamp_columns = subtable + "_initial_audit, " + subtable + "_last_audit"
                this_tablename = "audits_by_" + subtable
                # Cycle through audits
                # Select the The Latest pop for this audit
                pop_id_column = subtable + "_id, "
                # Also used on inserts
                select_columns = subtable + "_passed, " + subtable + "_failed, " + subtable + "_exempt "
                tablename = " from  " + this_tablename
                where_clause = " where " + subtable + "_text = '" + popSrvtype + "' "
                where_fk_audit = " and fk_audits_id = " + str(audit_id) + " "
                tail = " order by " + subtable + "_last_audit desc limit 1; "
                select_query = " select " + pop_id_column + select_columns + tablename + where_clause + where_fk_audit + tail

                # Debug

                cur.execute(select_query)
                if cur.rowcount :
                    # There's Data Check if it matches and then update or insert
                    this_pop_or_srvtype_data = cur.fetchone()
                    #print(this_pop_or_srvtype_data)
                    fail_column = subtable + "_failed"
                    pass_column = subtable + "_passed"
                    exempt_column = subtable + "_exempt"
                    id_column = subtable + "_id"

                    if this_pop_or_srvtype_data[fail_column] ==  this_fail and this_pop_or_srvtype_data[pass_column] == this_pass and this_pop_or_srvtype_data[exempt_column] == this_exem :
                        # Equals so update row
                        update_query = "UPDATE " + this_tablename + " SET " + subtable + "_last_audit = FROM_UNIXTIME(" + str(ANALYZE_TIME) + ") where " + id_column + " = '" + str(this_pop_or_srvtype_data[id_column]) + "' ; commit ; "
                        #print(update_query)
                        cur.execute(update_query)
                        insert_new = False
                    else:
                        # Need to do insert
                        #print(id_column + " needs insert")
                        insert_new = True
                else:
                    #print(id_column + " needs insert")
                    insert_new = True

                if insert_new :
                    # We've decided to insert a new row
                    columns = select_columns + ", fk_audits_id, " + subtable + "_text, " + this_timestamp_columns
                    values  = str(this_pass) + " , " + str(this_fail) + " , " + str(this_exem) + " , " + str(audit_id) + " , '" + popSrvtype  +\
                                "' ," + " FROM_UNIXTIME(" + str(ANALYZE_TIME) + "), " + "FROM_UNIXTIME(" + str(ANALYZE_TIME) + ") "
                    query_string = "INSERT INTO " + this_tablename + " ( " + columns + ") VALUES ( " + values + " ); commit; "
                    #print(query_string)
                    cur.execute(query_string)


        return "Completed"
    '''

    def giveMeDB(db_config_items) :

        db_conn = pymysql.connect(host=db_config_items['dbhostname'], port=int(db_config_items['dbport']), user=db_config_items['dbusername'], passwd=db_config_items['dbpassword'], db=db_config_items['dbdb'], autocommit=True)
        dbmessage = "Good, connected to " + db_config_items['dbusername'] + "@" + db_config_items['dbhostname'] + ":" + db_config_items['dbport'] + "/" + db_config_items['dbdb']
        analyze_stats["db-status"] = dbmessage

        return db_conn, dbmessage, analyze_stats

    # Globals
    global pop_results
    global srvtype_results
    global audit_results
    # Inserts Updates
    global audit_host_inserts
    global audit_host_updates


    pop_results = dict()
    pop_results_lock = threading.Lock()
    srvtype_results = dict()
    srvtype_results_lock = threading.Lock()
    audit_results = dict()
    audit_results_lock = threading.Lock()

    audit_host_inserts = 0
    audit_host_updates = 0
    audit_host_counts_lock = threading.Lock()

    MAX = db_config_items["collectionmaxchars"]
    FRESH = db_config_items["freshseconds"]
    MAXTHREADS = int(db_config_items["maxthreads"])


    # Create A Queue
    audit_queue = Queue()

    analyze_stats = dict()

    #try:
    db_conn, db_message, analyze_stats = giveMeDB(db_config_items)

    #except:
    #   analyze_stats["db-status"] = "Connection Failed"
    #   print(analyze_stats)


    host_good, analyze_stats["FreshHosts"], host_list = grab_host_list(db_conn, FRESH)

    if host_good :
        analyze_stats["HostCollectionStatus"] = "Success"
        # To avoid Locking pop stats are being moved to their own modul
        #analyze_stats["audit_inserts"], analyze_stats["audit_updates"], all_pop_results, all_srvtype_results, all_audit_results, jobtime = analyze_all_audits(db_config_items, host_list, FRESH, MAXTHREADS)
        analyze_stats["audit_inserts"], analyze_stats["audit_updates"], jobtime = analyze_all_audits(db_config_items, host_list, FRESH, MAXTHREADS)
        #print(audit_results)
        # Collation of Population Statistics is Being moved to It's own Module
        #try:
        #   analyze_stats["stor_pop_status"] = store_sub_results(db_conn, "pop" , all_pop_results)
        #except Exception as e :
        #   print("Error Storing Pop Results", e)
        #
        #try:
        #   analyze_stats["stor_srvytpe_status"] = store_sub_results(db_conn, "srvtype" , all_srvtype_results)
        #except Exception as e :
        #   print("Error Storing Srvtype Results", e)
        #
        #try:
        #   analyze_stats["stor_acoll_status"] = store_sub_results(db_conn, "acoll", all_audit_results)
        #except Exception as e :
        #   print("Error Storing Audit Results", e)

        analyze_stats["jobtime"] = str(jobtime)
        analyze_stats["threads"] = str(MAXTHREADS)
        analyze_stats["totalaudits"] = len(audits)

    else :
        analyze_stats["HostCollectionStatus"] = "Failed"

    print(json.dumps(analyze_stats, sort_keys=True, indent=4))


if __name__ == "__main__":
    analyze(CONFIGDIR, CONFIG)