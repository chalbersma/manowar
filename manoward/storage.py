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
import pprint

import pymysql

# Printing Stuff
from colorama import Fore, Back, Style

import manoward

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", help="JSON Config File with our Storage Info", required=False, default=None)
    parser.add_argument(
        "-j", "--json", help="json file to store", required=True)
    parser.add_argument("-v", "--verbose", action='append_const',
                        help="Turn on Verbosity", const=1, default=[])

    # Parser Args
    args = parser.parse_args()

    # Grab Variables
    JSONFILE = args.json
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

    LOGGER.info("Welcome to Storage Module")


# TODO remove this
def null_or_value(data_to_check, VERBOSE=False):

    logger = logging.getLogger("storage:null_or_value")

    if data_to_check == None:
        data = "NULL"
        return data
    else:
        data = "'" + str(data_to_check) + "'"
        return data


def insert_update_host(hostdata, db_conn):
    '''
    This updates the Host table (not the collections, sapi or ip_intel tables.

    The first step is to query for an existing record either by hostname or by hostid

    Important to note that this one opens it's own cursor from a connection to be more
    threadsafe. So it must close the cursor at the end of the query.
    '''

    logger = logging.getLogger("storage:insert_update_host")

    cur = db_conn.cursor()

    insert_columns = ["hostname", "last_update"]
    insert_values = ["%s", "FROM_UNIXTIME(%s)"]
    insert_columns_args = [
        hostdata["collection_hostname"], hostdata["collection_timestamp"]]

    host_id_query_params = list()

    # SELECT * Specification
    if isinstance(hostdata.get("uber_id", None), int):
        select_tail_specification = "from hosts where host_uber_id = %s "
        host_id_query_params.append(hostdata["uber_id"])
    else:
        select_tail_specification = "from hosts where hostname = %s"
        host_id_query_params.append(hostdata["collection_hostname"])

    select_head_specification = "SELECT host_id "
    host_id_query = "SELECT host_id {}".format(select_tail_specification)

    try:
        host_id_debug_query = cur.mogrify(host_id_query, host_id_query_params)
        logger.debug("Host ID Query : {}".format(host_id_debug_query))
        cur.execute(host_id_query, host_id_query_params)

    except Exception as insert_update_query_error:
        logger.error("{}Trouble with query for {} : {}{}".format(
            Fore.RED, str(host_id_query), str(e), Style.RESET_ALL))
    else:
        if not cur.rowcount:
            # No Results
            host_id = None
        else:
            # Not a Dict Response
            host_id = cur.fetchone()[0]

    logger.debug("Current Host to Insert Id : {}".format(host_id))

    # Add HostID Data To Columns, Matches and Values
    if host_id is not None:
        insert_columns.append("host_id")
        insert_values.append("%s")
        insert_columns_args.append(host_id)

    # Turn my Arguments into a JsonBlob for DB Insertion
    if isinstance(hostdata.get("arguments", None), dict):
        hostdata["args_json"] = json.dumps(hostdata["arguments"])

    # V2 Factors like pop srvtype and the like
    for v2factor in [("pop", "pop"),
                     ("srvtype", "srvtype"),
                     ("status", "hoststatus"),
                     ("uber_id", "host_uber_id"),
                     ("resource", "mresource"),
                     ("partition", "mpartition"),
                     ("service", "mservice"),
                     ("region", "mregion"),
                     ("mown_base", "mownbase"),
                     ("mown_full", "mownfull"),
                     ("args_json", "mowntags")]:
        if hostdata[v2factor[0]] != "N/A" and hostdata[v2factor[0]] is not None:
            insert_columns.append(v2factor[1])
            insert_values.append("%s")
            insert_columns_args.append(hostdata[v2factor[0]])
        else:
            logger.warning("No {0} given for host {1}, ignoring {0} column.".format(
                v2factor[0], hostdata["collection_hostname"]))

    replace_query = "REPLACE into hosts ( {} ) VALUES ( {} )".format(" , ".join(insert_columns),
                                                                     " , ".join(insert_values))

    try:
        replace_query_debug = cur.mogrify(replace_query, insert_columns_args)
        logger.debug("Replace Query for Host {} : {}".format(
            hostdata["collection_hostname"], replace_query_debug))
        cur.execute(replace_query, insert_columns_args)
    except Exception as replace_error:
        logger.error("Unable to do Replace Query for host {} with error : {}".format(
            hostdata["collection_hostname"], replace_query_debug))
    else:
        host_id = cur.lastrowid

    finally:
        db_conn.commit()
        cur.close()

    return host_id


def store_as_SAPI_host(host_id, db_conn, hostname, VERBOSE=False):
    '''
    Store as SAPI host. When we have a SAPI host we want to update the sapiActiveHosts table with that hostname
    so that we know we don't need to ssh to that in collections.
    '''

    logger = logging.getLogger("storage.py:store_as_SAPI_host")

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
                return_dictionary["updaterecord"] = "Record number : {}".format(
                    record_id_to_update)

            except Exception as sapi_update_sql_error:

                return_dictionary["error"] = True
                return_dictionary["error_text"] = str(sapi_update_sql_error)

                logger.error(
                    "Sapi Update SQL Error : {}".format(return_dictionary))

        else:
            # INSERT into sapiActiveHosts (fk_host_id, last_updated) VALUES ( %s , FROM_UNIXTIMESTAMP(%s));
            new_insert_sql = "INSERT into sapiActiveHosts (fk_host_id, last_updated, hostname) VALUES ( %s , FROM_UNIXTIME(%s), %s);"

            new_insert_values = (host_id, SAPI_STORE_TIME, hostname)

            try:
                cur.execute(new_insert_sql, new_insert_values)
                return_dictionary["success"] = True
                return_dictionary["insert_record"] = "Inserted New Record {}".format(
                    str(cur.lastrowid))
            except Exception as insert_sapi_sql_error:

                return_dictionary["error"] = True
                return_dictionary["error_text"] = str(insert_sapi_sql_error)

    return return_dictionary


def insert_update_collections(db_conn, host_id, hostdata, MAX):
    '''
    Insert Update collections.

    give me a list of collection items and I'll store them in the database.
    '''

    logger = logging.getLogger("storage:insert_update_collections")

    logger.debug("Storing Collections for host_id : {}".format(host_id))

    timestamp = hostdata["collection_timestamp"]

    cur = db_conn.cursor()

    error_count = 0
    inserts = 0
    updates = 0

    for ctype, ctype_dict in hostdata["collection_data"].items():

        for subtype, value in ctype_dict.items():

            killchars = "*;\\\'\"%="

            collection_type = str(ctype)[0:int(MAX)]

            collection_subtype = str(subtype)[0:int(MAX)]

            # Cycle throught value. Remove the banned characters and store it.
            collection_value = "".join(c for c in str(
                value)[0:int(MAX)] if c not in killchars)

            # Compare the value I have to the latest version
            find_existing_query_args = [str(host_id),
                                        str(collection_type),
                                        str(collection_subtype),
                                        str(collection_value)]

            # Encode the Fresh Time Stuff here
            find_existing_query = "SELECT {} {} {} {}".format(" collection_value, collection_id, last_update FROM collection ",
                                                              "WHERE fk_host_id = %s AND collection_type = %s ",
                                                              "AND collection_subtype = %s AND collection_value = %s ",
                                                              " Order by last_update desc limit 1 ")

            # See If I'm Updating This Result
            try:
                update_debug_query = cur.mogrify(
                    find_existing_query, find_existing_query_args)
                # Too Verbose even for Debug
                # logger.debug(update_debug_query)
                cur.execute(find_existing_query, find_existing_query_args)
            except Exception as update_collection_error:
                logger.error("{}Trouble with query {} on host {} with error : {}{}".format(Fore.RED,
                                                                                           find_existing_query,
                                                                                           host_id,
                                                                                           update_collection_error,
                                                                                           Style.RESET_ALL))
            else:

                updated = False

                if cur.rowcount:
                    #print(" There Is a RowCount")
                    matching_data = cur.fetchone()
                    # Grab 1:-1 to ignore the ' in 'value'
                    current_value = null_or_value(matching_data[0])[1:-1]
                    # Grab 1:-1 to ignore the ' in 'value'
                    current_collection_id = null_or_value(
                        matching_data[1])[1:-1]

                    current_last_update = int(datetime.datetime.strptime(null_or_value(
                        matching_data[2])[1:-1], '%Y-%m-%d %H:%M:%S').strftime("%s"))
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
                        update_query_args = [
                            str(timestamp), str(current_collection_id)]

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

                if not updated:
                    # Error
                    error_count += 1

    # Loop Completed
    db_conn.commit()
    cur.close()

    # Return Statistics
    return inserts, updates, error_count


def storage(config_items, hostdata, sapi=False):
    '''
    Does a Storage of an Object.
    '''

    logger = logging.getLogger("storage.py")

    STORAGE_TIME = int(time())
    storage_stats = dict()

    MAX = config_items["storage"]["collectionmaxchars"]

    storage_stats = dict()
    storage_stats["storage_timestamp"] = STORAGE_TIME

    db_conn = manoward.get_conn(
        config_items, prefix="store_", tojq=".database", ac_def=False)

    try:
        try:
            host_id = insert_update_host(hostdata, db_conn)
        except Exception as insert_update_host_error:
            logger.error("{}Unable to Update Host with Error : {}{}".format(Fore.RED,
                                                                            insert_update_host_error,
                                                                            Style.RESET_ALL))

            raise insert_update_host_error
        else:
            logger.info(host_id)

        # Unique Data FTM
        hostname = hostdata["collection_hostname"]

        storage_stats["collection_timestamp"] = hostdata["collection_timestamp"]

        try:
            storage_stats["inserts"], storage_stats["updates"], storage_stats["errors"] = insert_update_collections(db_conn,
                                                                                                                    host_id,
                                                                                                                    hostdata,
                                                                                                                    MAX)
        except Exception as insert_update_collections_error:
            logger.error("{}Unable to Update Collections associated with {}{}".format(Fore.RED,
                                                                                      hostname,
                                                                                      Style.RESET_ALL))
            logger.debug("Error : {}".format(insert_update_collections_error))

            raise insert_update_collections_error

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

        do_ipintel = config_items["ip_intel"].get("do_intel", False)

        logger.debug("Doing IP Intel. ({} Statement).".format(do_ipintel))

        if do_ipintel is True and "ip_intel" in hostdata.keys():
            # Process the IP Intelligence for this host
            result = manoward.process_ip_intel(config_dict=config_items,
                                               multireport=hostdata["ip_intel"],
                                               host_id=host_id)
            bad_results = [res for res in result if res not in (200, 202)]
            if len(bad_results) == 0:
                logger.info("{}IP Intel : {} for host {}{}".format(
                    Fore.GREEN, result, hostname, Style.RESET_ALL))
            else:
                logger.error("{}IP Intel : {} for host {}{}".format(
                    Fore.RED, result, hostname, Style.RESET_ALL))

    try:
        db_conn.commit()
        db_conn.close()
    except Exception as e:
        logger.error("{}Error Closing DB Connection{}".format(
            Fore.RED, Style.RESET_ALL))

    if __name__ == "__main__":
        print(json.dumps(storage_stats, sort_keys=True, indent=4))

    return storage_stats


if __name__ == "__main__":
    storage(CONFIG)
