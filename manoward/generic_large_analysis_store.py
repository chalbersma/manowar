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


def generic_large_analysis_store(db_conn, audit_id, audit_results_dict, FRESH):
    #print("in generic_large_compare")
    # Generic Large Analysis Storage

    # Create my Cursor
    logger = logging.getLogger("generic_large_analysis_store")

    ANALYZE_TIME = int(time())

    cur = db_conn.cursor()

    inserts = 0
    updates = 0

    audit_results_keys = dict()
    audit_results_updt = dict()

    # Create My Bucket Host ID Lists
    for bucket in audit_results_dict.keys():
        audit_results_keys[bucket] = list()
        audit_results_updt[bucket] = list()
        for host in audit_results_dict[bucket]:
            if "pfe" in host.keys():
                audit_results_updt[bucket].append(
                    [host["host_id"], host["pfe"], host["pfevalue"]])
                audit_results_keys[bucket].append(host["host_id"])

    # print(audit_results_keys)
    # print(audit_results_updt)

    # Do my Queries. Will have one Big select for each
    for bucket in audit_results_keys.keys():

        # Need to figure out why this isn't being picked up by bandit
        #bucket_ids_string = ",".join(map(str, audit_results_keys[bucket]))
        bucket_ids_paramertization_list = [
            " %s " for x in audit_results_keys[bucket]]

        bucket_ids_paramertization_list_string = " , ".join(
            map(str, bucket_ids_paramertization_list))

        pull_current_paramaters = [str(bucket)]

        pull_current_paramaters.extend(audit_results_keys[bucket])

        pull_current_paramaters.append(str(audit_id))
        pull_current_paramaters.append(str(FRESH))

        pull_current = list()
        pull_current.append(
            "SELECT audit_result_id, fk_host_id, audit_result, audit_result_text")
        pull_current.append("from audits_by_host")
        pull_current.append("where bucket = %s  ")
        pull_current.append(
            "and fk_host_id in (" + bucket_ids_paramertization_list_string + ")")
        pull_current.append("and fk_audits_id = %s ")
        pull_current.append("and last_audit >= now() - INTERVAL %s SECOND ")
        pull_current.append("group by fk_host_id order by last_audit desc ;")

        pull_current_query = " ".join(pull_current)

        if len(audit_results_keys[bucket]) > 0:
            # print(pull_current_query)
            cur.execute(pull_current_query, pull_current_paramaters)
            if cur.rowcount:
                current_audits_list = cur.fetchall()
            else:
                current_audits_list = []
        else:
            current_audits_list = []

        # print(audit_results_updt[bucket])
        # print(audit_results_keys[bucket])
        # print(current_audits_list)

        # Debug
        # if audit_id == 43 :
            #print("!!!!!!!!!!!!!!!!!!!!!!!!!!! HERE !!!!!!!!!!!!!!!!!!!!!!!!")

        # Find my Matches for this bucket These will have Updates Goin In.
            # Match PFE                                                                                     # Match PFE Value
        this_bucket_update = [audit_result for audit_result in current_audits_list if audit_result[2] == audit_results_updt[bucket][audit_results_keys[bucket].index(
            audit_result[1])][1] and audit_result[3] == audit_results_updt[bucket][audit_results_keys[bucket].index(audit_result[1])][2]]

        # Create an index to reference this_bucket_update
        this_bucket_update_index = [update_host_id[1]
                                    for update_host_id in this_bucket_update]

        # Find Items that Have no Equivalents in the Database. These will be inserts
        # Create an illegal audit id in position 0 just to be sure.
        # Grab the fk_host_id, pfe & pfe_value from the results passed to us.
        # Compare it against our index of update ready hosts to make sure it's not in both (As a system that doesn match an update will always require an insert)
        this_bucket_inserts = [(-1, new_audit_result[0], new_audit_result[1], new_audit_result[2])
                               for new_audit_result in audit_results_updt[bucket] if new_audit_result[0] not in this_bucket_update_index]

        # Updates
        # print("Updates")
        try:
            this_bucket_update_ids = [id[0] for id in this_bucket_update]
            if len(this_bucket_update_ids) > 0:
                #this_bucket_update_ids_string = ",".join(map(str, this_bucket_update_ids))

                # Make the , %s , %s for the in
                update_query_parameter_string_list = [
                    " %s " for x in this_bucket_update_ids]
                update_query_parameter_string = " , ".join(
                    map(str, update_query_parameter_string_list))

                # Paramertization
                update_query_parameters = [str(ANALYZE_TIME)]
                update_query_parameters.extend(this_bucket_update_ids)

                # This query is properly paramertizized
                # nosec
                update_query = "UPDATE audits_by_host SET last_audit = FROM_UNIXTIME( %s ) where audit_result_id in (" + \
                    update_query_parameter_string + ") "

                try:
                    example_sql = cur.mogrify(
                        update_query, update_query_parameters)
                    cur.execute(update_query, update_query_parameters)
                    updates += len(this_bucket_update_ids)
                except Exception as mysql_error:
                    print("Error updating hosts for audit",
                          audit_id, " : ", str(mysql_error))
        except Exception as updating_hosts_audit:
            logger.error("Error doing Updates for audit {} with error {}".format(audit_id,
                                                                                 updating_hosts_audit))

        # print("Inserts")

        try:
            if len(this_bucket_inserts) > 0:
                query_data = [[result[1], audit_id, ANALYZE_TIME, ANALYZE_TIME,
                               bucket, result[2], result[3]] for result in this_bucket_inserts]
                #print("Insert Data : " , query_data)
                # Only do this is there's stuff.
                insert_query = []
                insert_query.append(
                    "INSERT into audits_by_host ( fk_host_id, fk_audits_id, initial_audit, last_audit, bucket, audit_result, audit_result_text ) ")
                insert_query.append(
                    "VALUES( %s, %s, FROM_UNIXTIME(%s), FROM_UNIXTIME(%s), %s, %s, %s ) ")

                insert_query_string = " ".join(insert_query)

                try:
                    cur.executemany(insert_query_string, query_data)
                    inserts += len(this_bucket_inserts)
                except Exception as e:
                    print("Error doing Inserts for audit", audit_id, " : ", e)

        except Exception as inserts_new_host_audit:
            logger.error("Error doing Inserts for Audit {} with error {}".format(audit_id,
                                                                                 inserts_new_host_audit))

    # Close the MySQL Cursor
    cur.close()

    return inserts, updates
