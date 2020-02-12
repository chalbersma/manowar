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


def subtype_large_compare(db_conn, host_list_dict, mtype, ctype, csubtype, mvalue, FRESH):

    logger = logger.getLogger("subtype_large_compare")

    # Subtype Large Comparison

    cur = db_conn.cursor()

    results_dict = deepcopy(host_list_dict)

    # Host Lists
    host_ids_list = list()
    fail_hosts = list()
    success_hosts = list()
    exempt_hosts = list()

    inserts = 0
    updates = 0

    # Host ID
    for item in host_list_dict:
        host_ids_list.append(item['host_id'])

    # Massaging Types

    massaged_ctype = []
    massaged_csubtype = []
    massaged_mvalue = []

    # In order for each one. Rehydrate string (with ") and then convert to a tuple

    if type(ctype) is str:
        massaged_ctype.append(ctype)
    else:
        # It's a lists
        massaged_ctype = ctype

    if type(csubtype) is str:
        interm_processed_csubtype = ast.literal_eval(
            '"' + csubtype.replace(",", "\",\"") + '"')
        massaged_csubtype.append(interm_processed_csubtype)
    else:
        # Cycle through each subtype list and toss that into csubtype value
        massaged_csubtype = [ast.literal_eval(
            '"' + item.replace(",", "\",\"") + '"') for item in csubtype]

    if type(mvalue) is str:
        interm_processed_mvalue = ast.literal_eval(
            '"' + mvalue.replace(",", "\",\"") + '"')
        massaged_mvalue.append(interm_processed_mvalue)
    else:
        # Cycle throught the regexp matches and toss that into csubtype value
        massaged_mvalue = [ast.literal_eval(
            '"' + item.replace(",", "\",\"") + '"') for item in mvalue]

    #print(type(massaged_ctype), massaged_ctype)
    #print(type(massaged_csubtype), massaged_csubtype)
    #print(type(massaged_mvalue), massaged_mvalue)

    host_id_list_string = ",".join(map(str, host_ids_list))

    #print(type(host_id_list_string), host_id_list_string)
    #print("About to build Queries")

    for index_value in range(0, len(massaged_ctype)):

        if mtype == "subnonhere":
            # Both do the same thing. They just accept either a numerical match or a zero
            COMBINE = " OR "
            COLUMNMATCH = " = "
        elif mtype == "suballhere":
            COMBINE = " OR "
            COLUMNMATCH = " = "
        elif mtype == "subknowall":
            # subknowall
            COMBINE = " AND "
            COLUMNMATCH = " != "
        else:
            raise Exception("Unknown match type ", mtype)

        #print(COMBINE, COLUMNMATCH)
        # Cycle through each ctype & Do a Collection

        collection = []
        collection.append(
            "SELECT fk_host_id, count(DISTINCT(collection_subtype))")
        collection.append("from collection")
        collection.append("WHERE")
        # Where Host List
        collection.append(" ( fk_host_id in (" + host_id_list_string + ") )")
        collection.append(" AND ")
        collection.append(
            " ( collection_type = '" + str(massaged_ctype[index_value]) + "' )")
        collection.append(" AND ")
        collection.append(" ( ")

        # print(collection)

        # Grab the Column
        columns_only = []

        for sub_index_value in range(0, len(massaged_csubtype[index_value])):

            # Generate My Column Match String
            if massaged_mvalue[index_value][sub_index_value] == "any":
                matchstring = ""
            else:
                matchstring = " AND collection_value REGEXP '" + \
                    massaged_mvalue[index_value][sub_index_value] + "'"

            #print("Column Match: ", matchstring)

            columnmatch_string = "collection_subtype " + COLUMNMATCH + \
                "'" + massaged_csubtype[index_value][sub_index_value] + "'"

            columns_only.append("( " + columnmatch_string + matchstring + " )")

            # print(columns_only)

        columns_only_string = COMBINE .join(columns_only)

        collection.append(columns_only_string)
        collection.append(" ) ")

        collection.append(
            " and last_update >= now() - INTERVAL " + str(FRESH) + " SECOND ")
        collection.append(" group by fk_host_id order by last_update desc ;")

        collection_query = " ".join(collection)

        if len(host_ids_list) > 0:
            cur.execute(collection_query)
            if cur.rowcount:
                query_results_list = cur.fetchall()
            else:
                # No Results
                # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                query_results_list = []
        else:
            query_results_list = []

        # print(query_results_list)
        query_results_list_index = [host[0] for host in query_results_list]
        # print(query_results_list_index)

        exempthost = list()
        passhost = list()
        failhost = list()

        try:
            if mtype == "subnonhere":
                # No exempt hosts. All hosts not in our results pass
                exempthost = []
                passhost = [
                    host for host in host_ids_list if host not in query_results_list_index]
                failhost = [host[0]
                            for host in query_results_list if host[1] > 0]
            elif mtype == "suballhere":
                # All the hosts that Aren't in our query Results Fail
                exempthost = []
                # All the hosts in the results whose output matches exactly
                passhost = [host[0] for host in query_results_list if host[1] == len(
                    massaged_csubtype[index_value])]
                # All the hosts in our query results not in exempthosts or passhosts
                failhost = [host[0] for host in query_results_list if host[0]
                            not in exempthost and host[0] not in passhost]
            elif mtype == "subknowall":
                # No exempt hosts. Anything not in our list just fucking passed. :)
                exempthost = []
                # Pass host is all hosts that don't show up in query results
                passhost = [
                    host for host in host_ids_list if host not in query_results_list_index]
                failhost = [host[0]
                            for host in query_results_list if host[1] > 0]
            else:
                raise Exception(
                    "Unknown match type. Potential Race Condition!")
        except Exception as subtype_error:
            logger.error("Error Doing Comparisons {}".format(subtype_error))

        #print(exempthost, passhost, failhost)

        for host in range(0, len(results_dict)):
            # Hydrate if missing
            # print(host)
            try:
                if "pfe" in results_dict[host].keys():
                    if results_dict[host]['pfe'] == "fail":
                        # I've already failed so fuck you ( :) )
                        pass
                elif results_dict[host]['host_id'] in failhost:
                    # I've now failed so place this in the results This will overwrite any exempt or pass entries
                    results_dict[host]['pfe'] = "fail"
                    results_dict[host]['pfevalue'] = "Subtype Comparison " + \
                        mtype + " Failed"
                elif results_dict[host]['host_id'] in passhost:
                    results_dict[host]['pfe'] = "pass"
                    results_dict[host]['pfevalue'] = "Subtype Comparison " + \
                        mtype + " Passed"
                elif results_dict[host]['host_id'] in exempthost:
                    results_dict[host]['pfe'] = "notafflicted"
                    results_dict[host]['pfevalue'] = "Subtype Comparison " + \
                        mtype + " Exempt"
            except Exception as subtype_pfe_error:
                logger.error("Error tyring to match items relating to host {} with error {}".format(host,
                                                                                                    subtype_pfe_error))

    cur.close()

    return results_dict
