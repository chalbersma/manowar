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
#import apt_pkg
from copy import deepcopy
from time import time
from time import sleep
import logging

import threading
import multiprocessing
# Yes I use both!
from queue import Queue

import manoward

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", help="Main collate.ini file", required=False, default=False)
    parser.add_argument("-v", "--verbose", action='append_const',
                        help="Turn on Verbosity", const=1, default=[])

    parser._optionals.title = "DESCRIPTION "

    # Parser Args
    args = parser.parse_args()

    CONFIG = manoward.get_manoward(explicit_config=args.config)

    VERBOSE = len(args.verbose)

    if VERBOSE == 0:
        logging.basicConfig(level=logging.ERROR)
    elif VERBOSE == 1:
        logging.basicConfig(level=logging.WARNING)
    elif VERBOSE == 2:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)


def collate(CONFIG):

    logger = logging.getLogger("collate")

    COLLATION_TIME = int(time())

    # Better Fresh Info/Unifies Lists between what is returned by the api (auditresults)
    # And what's returned by collate (powers the dashboard).
    seconds_after_midnight = COLLATION_TIME % 86400
    MIDNIGHT = COLLATION_TIME - seconds_after_midnight
    twodaytimestamp = MIDNIGHT - (86400*2)

    # Parse my General Configuration
    if isinstance(CONFIG, dict):
        config_items = CONFIG
    elif isinstance(CONFIG, str):
        config_items = manoward.get_manoward(explicit_config=CONFIG)
    else:
        raise TypeError("No Configuration Given.")

    '''
    def giveMeDB(db_config_items) :

        db_conn = pymysql.connect(host=db_config_items['dbhostname'], port=int(db_config_items['dbport']), user=db_config_items['dbusername'], passwd=db_config_items['dbpassword'], db=db_config_items['dbdb'], autocommit=True)
        dbmessage = "Good, connected to " + db_config_items['dbusername'] + "@" + db_config_items['dbhostname'] + ":" + db_config_items['dbport'] + "/" + db_config_items['dbdb']

        return db_conn, dbmessage
    '''

    def grab_single_collated(db_config, result_enum, type_to_grab):

        logger = logging.getLogger("grab_single_collated")

        db_conn = manoward.get_conn(
            db_config, prefix="analyze_", tojq=".database", ac_def=True)

        cur = db_conn.cursor()

        # Check Result Enum
        if result_enum not in ["pass", "fail", "notafflicted"]:
            raise Exception(
                "Result Enum not in pass/fail/notafflicted. Instead it's : ", str(results_enum))

        if type_to_grab not in ["acoll", "pop", "srvtype"]:
            raise Exception(
                "Type to Grab Unknown. Not in acoll, pop, srvtype instead it's : ", str(type_to_grab))

        if type_to_grab == "acoll":
            grouper = "audits.audit_name"
            table = "audits_by_acoll"
        elif type_to_grab == "pop":
            grouper = "hosts.pop"
            table = "audits_by_pop"
        elif type_to_grab == "srvtype":
            grouper = "hosts.srvtype"
            table = "audits_by_srvtype"

        grab_single_collated_query_list = list()
        grab_single_collated_query_list.append(
            "SELECT " + grouper + ", fk_audits_id, count(DISTINCT fk_host_id) ")
        grab_single_collated_query_list.append("FROM audits_by_host ")
        grab_single_collated_query_list.append(
            "join hosts on fk_host_id =  hosts.host_id ")
        grab_single_collated_query_list.append(
            "join audits on fk_audits_id =  audits.audit_id ")
        grab_single_collated_query_list.append("WHERE")
        grab_single_collated_query_list.append("audit_result = %s ")
        grab_single_collated_query_list.append(
            "and last_audit >= FROM_UNIXTIME(%s) ")
        grab_single_collated_query_list.append(
            "group by " + grouper + ", fk_audits_id")

        grab_scq_args = [result_enum, twodaytimestamp]

        grab_single_collated_query = " ".join(grab_single_collated_query_list)

        # print(grab_single_collated_query)

        try:
            gsqq_debug = cur.mogrify(grab_single_collated_query, grab_scq_args)
            logger.debug("GSQQ Debug : {}".format(gsqq_debug))
            cur.execute(grab_single_collated_query, grab_scq_args)
        except Exception as gscq_query_error:
            logger.error("Unable to Grab GSCQ Error for Group : {} on type {}".format(
                grouper, type_to_grab))
            raise gscq_query_error
        else:

            if cur.rowcount:
                query_results_list = cur.fetchall()
            else:
                # No Results
                # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                query_results_list = list()
        finally:
            cur.close()

        return query_results_list

    def grab_multiple_collated(db_config, type_to_grab):

        logger = logging.getLogger("grab_multiple_collated")

        # TODO Argumentize this one.
        if type_to_grab not in ["acoll", "pop", "srvtype"]:
            raise Exception(
                "Type to Grab Unknown. Not in acoll, pop, srvtype instead it's : ", str(type_to_grab))

        full_results_list = dict()

        for item in ["pass", "fail", "notafflicted"]:
            this_results_list = grab_single_collated(
                db_config, item, type_to_grab)

            # print(this_results_list)

            for result in this_results_list:
                # Create an Entry For each result type (pop, srvtype or audit)
                if result[0] not in full_results_list.keys():
                    # No Entry so Create a New Result Dict
                    full_results_list[result[0]] = dict()
                    # Add the fk_audit_id Number for Reference
                    #full_results_list[result[0]]["fk_audits_id"] = result[1]
                # Create an Entry For each Audit for this result type
                if result[1] not in full_results_list[result[0]].keys():
                    full_results_list[result[0]][result[1]] = dict()

                # Add my item (but to the real place now
                full_results_list[result[0]][result[1]][item] = result[2]

        return full_results_list

    def grab_all_table_data(db_config):

        logger = logging.getLogger("grab_all_table_data")

        updates = 0
        inserts = 0

        for table in ["acoll", "pop", "srvtype"]:

            table_results = grab_multiple_collated(db_config, table)

            current_table_results = get_current_table_data(db_config, table)

            this_updates, this_inserts = compare_update_insert_table(
                table_results, current_table_results, table, db_config)

            updates += this_updates
            inserts += this_inserts

            logger.debug("For table {} I:{} U:{}".format(
                table, this_inserts, this_updates))

        return updates, inserts

    def compare_update_insert_table(collected, currently_on_disk, table, db_config):

        logger = logging.getLogger("compare_update_insert_table")

        updates = 0
        inserts = 0

        db_conn = manoward.get_conn(
            db_config, prefix="analyze_", tojq=".database", ac_def=True)

        COLLATE_TIME = int(time())

        cur = db_conn.cursor()

        collected_index = list()

        # Hydrate Collecteded Items
        for index in collected.keys():

            for this_audit_id in collected[index].keys():

                collected_index.append((index, this_audit_id))

                # Hydrate this
                if "pass" not in collected[index][this_audit_id].keys():
                    collected[index][this_audit_id]["pass"] = 0

                if "fail" not in collected[index][this_audit_id].keys():
                    collected[index][this_audit_id]["fail"] = 0

                if "notafflicted" not in collected[index][this_audit_id].keys():
                    collected[index][this_audit_id]["notafflicted"] = 0

        #print("Hydrated Collections", collected)
        #print("Collected Index", collected_index)

        # Compare My Stuff (Get a list of update hosts and insert hosts
        #print("Current Amounts", currently_on_disk)

        # IDs to Update Used in SQL
        update_ids = [item[0] for item in currently_on_disk
                      if item[1] in collected.keys()
                      and item[2] in collected[item[1]].keys()
                      and collected[item[1]][item[2]]["pass"] == item[3]
                      and collected[item[1]][item[2]]["fail"] == item[4]
                      and collected[item[1]][item[2]]["notafflicted"] == item[5]
                      ]

        # Items to Insert
        # Part of What's Needed
        current_text_location = dict()

        for i in range(0, len(currently_on_disk)):

            #print(currently_on_disk[i][1], currently_on_disk[i][2])

            if currently_on_disk[i][1] not in current_text_location.keys():
                current_text_location[currently_on_disk[i][1]] = dict()

            if currently_on_disk[i][2] not in current_text_location[currently_on_disk[i][1]].keys():
                current_text_location[currently_on_disk[i]
                                      [1]][currently_on_disk[i][2]] = i

        #print("On Disk Lookups", current_text_location)

        insert_list = list()
        insert_list = [[item[0], item[1], COLLATE_TIME, COLLATE_TIME, collected[item[0]][item[1]]["pass"], collected[item[0]][item[1]]["fail"], collected[item[0]][item[1]]["notafflicted"]]
                       for item in collected_index
                       if item[0] not in current_text_location.keys() or item[1] not in current_text_location[item[0]].keys() or (collected[item[0]][item[1]]["pass"], collected[item[0]][item[1]]["fail"], collected[item[0]][item[1]]["notafflicted"])
                       != (currently_on_disk[current_text_location[item[0]][item[1]]][3], currently_on_disk[current_text_location[item[0]][item[1]]][4], currently_on_disk[current_text_location[item[0]][item[1]]][5])]

        logger.debug("Update IDs : {}".format(update_ids))
        logger.debug("Insert List : {}".format(insert_list))

        try:
            if len(update_ids) > 0:
                #update_ids_string = ",".join(map(str, update_ids))
                # Update ID's will now be used as a query paramertization list
                update_ids_parameters = [" %s " for x in update_ids]
                update_ids_string = ",".join(map(str, update_ids_parameters))
                update_query_parameters = [str(COLLATE_TIME)]
                update_query_parameters.extend(update_ids)
                # Query has been parameterized
                update_query = "UPDATE "
                update_query = update_query + "audits_by_" + table + " SET " + table +\
                    "_last_audit = FROM_UNIXTIME( %s ) where " +\
                    table +\
                    "_id in ( " + update_ids_string + " ) "

                try:
                    update_query_debug = cur.mogrify(
                        update_query, update_query_parameters)

                    logger.info(
                        "Running Update Query for table : {}".format(table))
                    logger.debug("{}".format(table, update_query_debug))

                    cur.execute(update_query, update_query_parameters)
                except Exception as update_query_error:
                    logger.error("Error updating hosts for {} : {}".format(
                        table, update_query_error))
                else:
                    updates += len(update_ids)

        except Exception as update_error:
            logger.error("Error doing Updates. {}".format(update_error))

        # Inserts

        try:
            if len(insert_list) > 0:

                # Only do this is there's stuff.
                insert_query = []
                # This query is properly paramaterized and the table value is properly
                # hardcoded earlier in the program. I'm noseccing it.
                insert_query.append(
                    "INSERT into audits_by_{0} ( {0}_text, ".format(table))  # nosec
                insert_query.append(
                    "fk_audits_id, {0}_initial_audit, {0}_last_audit, {0}_passed, {0}_failed, {0}_exempt ) ".format(table))
                insert_query.append(
                    "VALUES( %s, %s, FROM_UNIXTIME(%s), FROM_UNIXTIME(%s), %s, %s, %s ) ")

                insert_query_string = " ".join(insert_query)

                try:
                    cur.executemany(insert_query_string, insert_list)
                except Exception as insert_query_error:
                    logger.error("Error doing Inserts for {} : {}".format(
                        table, insert_error))
                else:
                    inserts += len(insert_list)

        except Exception as insert_error:
            logger.error("Error doing Inserts : {}".format(insert_error))

        return updates, inserts

    def get_current_table_data(db_config, table):

        db_conn = manoward.get_conn(
            db_config, prefix="analyze_", tojq=".database", ac_def=True)

        cur = db_conn.cursor()

        grab_current_table_list = list()
        grab_current_table_list.append(
            "SELECT {0}_id, {0}_text, fk_audits_id, {0}_passed, {0}_failed, {0}_exempt ".format(table))
        grab_current_table_list.append("FROM audits_by_{0}".format(table))
        grab_current_table_list.append(
            "WHERE {0}_last_audit >= now() - INTERVAL %s SECOND".format(table))
        grab_current_table_list.append(
            "group by {0}_text, fk_audits_id".format(table))

        grab_ctl_args = [db_config["collate"]["freshseconds"]]

        grab_current_table_query = " ".join(grab_current_table_list)

        # print(grab_current_table_query)
        try:
            cur.execute(grab_current_table_query, grab_ctl_args)
        except Exception as grab_ctl_query_error:
            logger.error(
                "Unable to grab current table list table {}".format(table))
        else:
            if cur.rowcount:
                query_results_list = cur.fetchall()
            else:
                query_results_list = list()
        finally:
            cur.close()

        return query_results_list

    # Globals
    FRESH = config_items["collate"]["freshseconds"]

    results_dict = dict()

    results_dict["updates"], results_dict["inserts"] = grab_all_table_data(
        config_items)

    return results_dict


if __name__ == "__main__":
    results = collate(CONFIG)

    print(json.dumps(results, sort_keys=True, indent=4))
