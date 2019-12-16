#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import argparse
from configparser import ConfigParser
from time import time
import datetime
import logging
import json
import sys
import ast

import pymysql

# Printing Stuff
from colorama import Fore, Back, Style
import pprint

# IP Intelligence
from process_ip_intel import process_ip_intel


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="JSON Config File with our Storage Info", required=True)
    parser.add_argument("-j", "--json", help="json file to store", required=True)
    parser.add_argument("-v", "--verbose", action='append_const', help="Turn on Verbosity", const=1, default=[])

    parser._optionals.title = "DESCRIPTION "

    # Parser Args
    args = parser.parse_args()

    # Grab Variables
    JSONFILE = args.json
    CONFIG = args.config

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

    LOGGER.info("Welcome to Storage Module")


def storage(CONFIG, JSONFILE, VERBOSE=False, sapi=False):

    logger = logging.getLogger("storage.py")

    STORAGE_TIME = int(time())
    storage_stats = dict()

    try:
        # Read Our INI with our data collection rules
        config = ConfigParser()
        config.read(CONFIG)
        # Debug
        #for i in config :
            #for key in config[i] :
                #print (i, "-", key, ":", config[i][key])
    except Exception as e: # pylint: disable=broad-except, invalid-name
        storage_stats["config-parse-status"] = "Failure with " + str(e)

        if __name__ == "__main__":
            print(json.dumps(storage_stats, sort_keys=True, indent=4))
            exit(1)

        return storage_stats



    db_config_items = dict()
    ip_intel_config = dict()
    # Collection Items
    for section in config:
        if section == "database":
            for item in config[section]:
                db_config_items[item] = config[section][item]
        if section == "ip_intel":
            for item in config[section]:
                ip_intel_config[item] = ast.literal_eval(config[section][item])

    MAX = db_config_items["collectionmaxchars"]

    storage_stats = dict()
    storage_stats["storage_timestamp"] = STORAGE_TIME

    try:
        db_conn = pymysql.connect(host=db_config_items['dbhostname'],
                                  port=int(db_config_items['dbport']),
                                  user=db_config_items['dbusername'],
                                  passwd=db_config_items['dbpassword'],
                                  db=db_config_items['dbdb'])

        dbmessage = "Good, connected to {}@{}:{}/{}".format(db_config_items['dbusername'],
                                                            db_config_items['dbhostname'],
                                                            db_config_items['dbport'],
                                                            db_config_items['dbdb'])

        storage_stats["db-status"] = dbmessage

    except Exception as dbconnection_error:
        storage_stats["db-status"] = "Connection Failed"
        storage_stats["db-error"] = str(dbconnection_error)
        return storage_stats

    collection_good, hostdata, results_data = parse_json_file(JSONFILE=JSONFILE)
    storage_stats["collection_status"] = collection_good


    if collection_good:
        try:
            host_id = insert_update_host(hostdata, db_conn)
            hostname = hostdata["hostname"]
            storage_stats["collection_timestamp"] = hostdata['last_update']
            storage_stats["inserts"], storage_stats["updates"], storage_stats["errors"] = insert_update_collections(db_conn,
                                                                                                                    host_id,
                                                                                                                    results_data,
                                                                                                                    MAX,
                                                                                                                    hostdata['last_update'],
                                                                                                                    hostname)

        except Exception as dbconnection_error:
            logger.error("{}Error Updating Host Collecitons {}{}".format(Fore.RED,
                                                                         dbconnection_error,
                                                                         Style.RESET_ALL))

            storage_stats["insert_update"] = 0
            storage_stats["errors"] = 1
        else:
            logger.info("{}Updating Collection Success{}{}".format(Fore.GREEN,
                                                                   storage_stats,
                                                                   Style.RESET_ALL))

            # Updating Collection has been a success Let's check if this is a sapi host.
            if sapi is True:
                # I am so update sapi table
                storage_stats["sapi_data"] = store_as_SAPI_host(host_id=host_id,
                                                                db_conn=db_conn,
                                                                hostname=hostname)

            do_ipintel = ip_intel_config.get("do_intel", False)

            logger.debug("Doing IP Intel. ({} Statement).".format(do_ipintel))

            if do_ipintel == True and "ip_intel" in hostdata.keys():
                # Process the IP Intelligence for this host
                result = process_ip_intel(config_dict={"ip_intel" : ip_intel_config},
                                          multireport=hostdata["ip_intel"],
                                          host=hostname)
                if result == 200:
                    logger.info("{}IP Intel : {} for host {}{}".format(Fore.GREEN, result, hostname, Style.RESET_ALL))
                else:
                    logger.error("{}IP Intel : {} for host {}{}".format(Fore.RED, result, hostname, Style.RESET_ALL))

    else:
        storage_stats["inserts_updates"] = 0
        storage_stats["errors"] = 1



    try:
        db_conn.commit()
        db_conn.close()
    except Exception as e:
        logger.error("{}Error Closing DB Connection{}".format(Fore.RED, Style.RESET_ALL))

    if __name__ == "__main__":
        print(json.dumps(storage_stats, sort_keys=True, indent=4))

    return storage_stats

def parse_json_file(JSONFILE=False, VERBOSE=False):

    logger = logging.getLogger("storage:parse_json_file")

    # Return: collection_good, hostdata, results_data
    collection_good = False

    # If we've got the dict passed to us instead of the filename
    if isinstance(JSONFILE, dict):
        # Treat the dict as the results
        collection_results = JSONFILE
    else:
        # Generally means we're running it manually
        with open(JSONFILE) as json_file:
            # Parse my JSONFILE as a file and load it to a dict
            collection_results = json.load(json_file)

    # No matter what check to see that I have "SSH SUCCESS" (Future more) in my collection_status
    # Future will have more successful types
    if collection_results['collection_status'] in ["SSH SUCCESS", "STINGCELL"]:
        # Do Parse stuff
        collection_good = True
        hostdata = {
                        "host_uber_id" : collection_results['uber_id'],
                        "hostname" : collection_results['collection_hostname'],
                        "pop" : collection_results['pop'],
                        "srvtype" : collection_results['srvtype'],
                        "last_update" : collection_results['collection_timestamp'],
                        "status" : collection_results['status']
                        }
        results_data = collection_results['collection_data']

        if "ip_intel" in collection_results:
            hostdata["ip_intel"] = collection_results["ip_intel"]

    else:
        # Failed for some reason. Ignoring any results.
        print(collection_results["status"])
        collection_good = False
        hostdata = dict()
        results_data = dict()

    return collection_good, hostdata, results_data

def null_or_value(data_to_check, VERBOSE=False):

    logger = logging.getLogger("storage:null_or_value")

    if data_to_check == None:
        data = "NULL"
        return data
    else:
        data = "'" + str(data_to_check) + "'"
        return data

def insert_update_host(hostdata, db_conn, VERBOSE=False):

    logger = logging.getLogger("storage:insert_update_host")

    cur = db_conn.cursor()

    # TODO Replace this with
    # Always Columns
    column_string = "hostname, last_update"
    # Always Values
    values_string = "'{}', FROM_UNIXTIME({}) ".format(hostdata['hostname'], str(hostdata['last_update']))

    # SELECT * Specification
    if hostdata['host_uber_id'] != "N/A":
        # Host_uber_id Given
        # <SELECT host_id> from hosts where [ host_uber_id = hostdata['host_uber_id']
        select_tail_specification = "from hosts where host_uber_id =  '" + str(hostdata['host_uber_id']) + "' ;"
    else:
        select_tail_specification = "from hosts where hostname =  '" + str(hostdata['hostname']) + "' ;"

    ####################################################################
    # Add host_id
    # No If there's not specifing this
    select_head_specification = "SELECT host_id "
    host_id_query = select_head_specification + select_tail_specification

    try:
        cur.execute(host_id_query)
    except Exception as insert_update_query_error:
        logger.error("{}Trouble with query {} : {}{}".format(Fore.RED, str(host_id_query), str(e), Style.RESET_ALL))

    if not cur.rowcount:
        # No Results
        host_id_data = "NULL"
    else:
        this_host_id_data = cur.fetchone()[0]
        host_id_data = null_or_value(this_host_id_data)

    column_string = "host_id, " + column_string
    values_string = host_id_data + ", " + values_string
    ####################################################################

    ####################################################################
    # Add POP
    if hostdata['pop'] == "N/A":
        # Do a Select to see if POP is in the DB
        select_head_specification = "SELECT pop "
        pop_query = select_head_specification + select_tail_specification

        try:
            cur.execute(pop_query)
        except Exception as pop_query_error:
            logger.error("{}Trouble with query {}:{}{}".format(Fore.RED, pop_query, pop_query_error, Style.RESET_ALL))

        if not cur.rowcount:
            # No Results
            pop_data = "NULL"
        else:
            this_pop_data = cur.fetchone()[0]
            pop_data = null_or_value(this_pop_data)
    else:
        # POP Data Given Always Overwrite
        pop_data = "'{}'".format(hostdata['pop'])

    column_string = column_string + ", pop"
    values_string = values_string + ", " + pop_data

    # Add srvtype
    if hostdata['srvtype'] == "N/A":
        # Do a Select to see if SRVTYPE is in the DB
        select_head_specification = "SELECT srvtype "
        srvtype_query = select_head_specification + select_tail_specificationkj

        try:
            cur.execute(srvtype_query)
        except Exception as srvtype_select_error:
            logger.error("{}Trouble with query {}:{}{}".format(Fore.RED, srvtype_query, srvtype_select_error, Style.RESET_ALL))

        if not cur.rowcount:
            # No Results
            srvtype_data = "NULL"
        else:
            this_srvtype_data = cur.fetchone()[0]
            srvtype_data = null_or_value(this_srvtype_data)
    else:
        # POP Data Given Always Overwrite
        srvtype_data = "'{}'".format(hostdata['srvtype'])

    column_string = column_string + ", srvtype"
    values_string = values_string + ", " + srvtype_data

    # Add hoststatus
    if hostdata['status'] == "N/A":
        # Do a Select to see if SRVTYPE is in the DB
        select_head_specification = "SELECT hoststatus "
        status_query = select_head_specification + select_tail_specification

        try:
            cur.execute(status_query)
        except Exception as select_hoststatus_error:
            logger.error("{}Trouble with query {}:{}{}".format(Fore.RED, status_query, select_hoststatus_error, Style.RESET_ALL))

        if not cur.rowcount:
            # No Results
            status_data = "NULL"
        else:
            this_status_data = cur.fetchone()[0]
            status_data = null_or_value(this_status_data)
    else:
        # POP Data Given Always Overwrite
        status_data = "'{}'".format(hostdata['status'])

    column_string = column_string + ", hoststatus"
    values_string = values_string + ", " + status_data

    # Add host_uber_id
    if hostdata['host_uber_id'] == "N/A":
        # Do a Select to see if SRVTYPE is in the DB
        select_head_specification = "SELECT host_uber_id "
        host_uber_id_query = select_head_specification + select_tail_specification

        try:
            cur.execute(host_uber_id_query)
        except Exception as select_host_uber_id:
            logger.error("{}Trouble with query {}:{}{}".format(Fore.RED, host_uber_id_query, select_host_uber_id, Style.RESET_ALL))

        if not cur.rowcount:
            # No Results
            host_uber_id_data = "NULL"
        else:
            this_host_uber_id_data = cur.fetchone()[0]
            host_uber_id_data = null_or_value(this_host_uber_id_data)
    else:
        # POP Data Given Always Overwrite
        host_uber_id_data = "'{}'".format(hostdata['host_uber_id'])

    column_string = column_string + ", host_uber_id"
    values_string = values_string + ", " + host_uber_id_data
    ####################################################################

    query_head = "REPLACE into hosts ( "
    query_mid = " ) VALUES ( "
    query_tail = " ) ; "
    query_string = query_head + column_string + query_mid + values_string + query_tail
    #print(query_string)

    cur.execute(query_string)
    #print("Problem with query : " + query_string )
    #print("Error: " + str(sys.exc_info()[0] )

    this_row = cur.lastrowid
    db_conn.commit()
    cur.close()

    return this_row



def store_as_SAPI_host(host_id, db_conn, hostname, VERBOSE=False):

    SAPI_STORE_TIME = int(time())

    return_dictionary = dict()

    cur = db_conn.cursor(pymysql.cursors.DictCursor)

    # SELECT sapihost_record from sapiActiveHosts where fk_host_id = %s and last_updated >= (now() - INTERVAL 3 DAY) limit 1;

    find_sapi_record_sql = "SELECT sapihost_record from sapiActiveHosts where fk_host_id = %s and last_updated >= (now() - INTERVAL 3 DAY) limit 1;"

    find_sapi_record_values = (host_id)

    try:
        cur.execute(find_sapi_record_sql, find_sapi_record_values)
    except Exception as sapi_store_error:
        logger.error("{}Trouble with query {}:{}{}".format(Fore.RED,
                                                           find_sapi_record_sql,
                                                           sapi_store_error,
                                                           Style.RESET_ALL))

        return_dictionary["error"] = True
        return_dictionary["error_text"] = str(sapi_store_error)
    else:
        if cur.rowcount:

            # We have a Row so grab and update
            matching_data = cur.fetchone()
            record_id_to_update = matching_data["sapihost_record"]

            # UPDATE sapiActiveHosts where sapihost_record = %s
            # Schema will update timestamp.

            update_sql = "UPDATE sapiActiveHosts set  last_updated=FROM_UNIXTIME(%s)  where sapihost_record = %s ; "
            update_values = (SAPI_STORE_TIME, record_id_to_update)

            try:
                cur.execute(update_sql, update_values)

                return_dictionary["success"] = True
                return_dictionary["updaterecord"] = "Record number : {}".format(record_id_to_update)

            except Exception as sapi_update_sql_error:

                return_dictionary["error"] = True
                return_dictionary["error_text"] = str(sapi_update_sql_error)

                logger.error("Sapi Update SQL Error : {}".format(return_dictionary))

        else:
            # INSERT into sapiActiveHosts (fk_host_id, last_updated) VALUES ( %s , FROM_UNIXTIMESTAMP(%s));
            new_insert_sql = "INSERT into sapiActiveHosts (fk_host_id, last_updated, hostname) VALUES ( %s , FROM_UNIXTIME(%s), %s);"

            new_insert_values = (host_id, SAPI_STORE_TIME, hostname)

            try:
                cur.execute(new_insert_sql, new_insert_values)
                return_dictionary["success"] = True
                return_dictionary["insert_record"] = "Inserted New Record {}".format(str(cur.lastrowid))
            except Exception as insert_sapi_sql_error:

                return_dictionary["error"] = True
                return_dictionary["error_text"] = str(insert_sapi_sql_error)

    return return_dictionary


def insert_update_collections(db_conn, host_id, results_data, MAX, timestamp, hostname, VERBOSE=False):

    '''
    Insert Update collections.

    give me a list of collection items and I'll store them in the database.
    '''

    logger = logging.getLogger("storage:insert_update_collections")

    cur = db_conn.cursor()


    error_count = 0
    inserts = 0
    updates = 0
    for item in results_data:
        if "collection_failed" in results_data[item]:

            logger.info("{}{}Collection Failed for {} on host: {}{}".format(Back.CYAN, Fore.BLACK,
                                                                            item, hostname,
                                                                            Style.RESET_ALL))
            error_count += 1
            continue
        else:
            # No Error for this item Cycle through the collection
            for collection in results_data[item]:
                #print(collection)
                killchars = "*;\\\'\"%="
                collection_type = str(item)[0:int(MAX)]
                collection_subtype = str(collection)[0:int(MAX)]

                # Cycle throught value. Remove the banned characters and store it.
                collection_value = "".join(c for c in str(results_data[item][collection])[0:int(MAX)] if c not in killchars)

                # Compare the value I have to the latest version
                find_existing_query_args = [str(host_id),
                                            str(collection_type),
                                            str(collection_subtype),
                                            str(collection_value)]

                find_existing_query = "SELECT "
                find_existing_query = find_existing_query +\
                                         " collection_value, collection_id, last_update FROM collection " +\
                                        "WHERE fk_host_id = %s AND collection_type = %s " +\
                                        "AND collection_subtype = %s AND collection_value = %s " +\
                                        " Order by last_update desc limit 1 ; "

                try:
                    cur.execute(find_existing_query, find_existing_query_args)
                except Exception as update_collection_error:
                    logger.error("{}Trouble with query {} on host {} with error : {}{}".format(Fore.RED,
                                                                                               find_existing_query,
                                                                                               hostname,
                                                                                               update_collection_error,
                                                                                               Style.RESET_ALL))

                updated = False

                if cur.rowcount:
                    #print(" There Is a RowCount")
                    matching_data = cur.fetchone()
                    # Grab 1:-1 to ignore the ' in 'value'
                    current_value = null_or_value(matching_data[0])[1:-1]
                    # Grab 1:-1 to ignore the ' in 'value'
                    current_collection_id = null_or_value(matching_data[1])[1:-1]

                    current_last_update = int(datetime.datetime.strptime(null_or_value(matching_data[2])[1:-1], '%Y-%m-%d %H:%M:%S').strftime("%s"))
                    #current_last_update = int(time.strptime(null_or_value(matching_data[2])[1:-1], '%Y-%m-%d %H:%M:%S'))
                    if not timestamp > current_last_update:
                        # If the timestamp from this collection is not greater than what I have in the database ignore
                        # Ignoring because of old data
                        error_count += 1
                        # We've don all the updates we care about. Get me outta here.
                        updated = True
                    elif current_value == collection_value:
                        # Update Timestamp Change My Bool Flag
                        # & new timestamp is better than last timestamp
                        update_query_args = [str(timestamp), str(current_collection_id)]

                        update_query = "UPDATE collection SET last_update = FROM_UNIXTIME( %s ) WHERE collection_id = %s ;"

                        try:
                            cur.execute(update_query, update_query_args)
                        except Exception as update_collection_timestamp_error:
                            logger.error("{}Trouble with query {}:{}{}".format(Fore.RED,
                                                                               update_query,
                                                                               update_query_args,
                                                                               Style.RESET_ALL))

                        updated = True
                        updates += 1
                        continue

                if not updated:
                    #print("Insert Brand Spaking New")
                    # Because there was no collection (new Collection) Or Old Collection Didn't Match
                    insert_query_head = " INSERT into collection ( fk_host_id, initial_update, last_update, collection_type, collection_subtype, collection_value ) "
                    insert_query_mid = " VALUES (%s, FROM_UNIXTIME(%s), FROM_UNIXTIME(%s), %s , %s , %s)"
                    insert_query_tail = "; "

                    insert_query = insert_query_head + insert_query_mid + insert_query_tail

                    insert_query_args = [host_id,
                                         timestamp,
                                         timestamp,
                                         collection_type,
                                         collection_subtype,
                                         collection_value]

                    try:
                        cur.execute(insert_query, insert_query_args)
                    except Exception as insert_new_collection_error:
                        logger.error("{}Trouble with query {} : {}{}".format(Fore.RED,
                                                                             insert_query,
                                                                             insert_new_collection_error,
                                                                             Style.RESET_ALL))

                    inserts += 1
                    updated = True

                # Commit My Recent Changes
                db_conn.commit()
                if not updated:
                    # Error
                    error_count += 1

                # Keep this in here while Troubleshooting. Will stop the storage after each type
                #break

    # Loop Completed
    # Close Cursor
    db_conn.commit()
    cur.close()

    # Return Statistics
    return inserts, updates, error_count

if __name__ == "__main__":
    storage(CONFIG, JSONFILE)
