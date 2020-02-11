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
import packaging.version
from copy import deepcopy
from time import time
from time import sleep
import logging

import threading
import multiprocessing
# Yes I use both!
from queue import Queue


def generic_large_compare(db_conn, host_list_dict, mtype, ctype, csubtype,
                          mvalue, FRESH=172800, exemptfail=False, audit_name="not_given"):
    '''
    generic_large_compare


    host_list_dict is an array with a dict describing the host that array looks like this:

        [{ host_id : int(),
          pop : string(),
          srvtype: string(),
          last_update: datetime.datetime()
        }]

    mtype is a string that has one of the accepted comparison types

    ctype is an array that describes the collection type that has a list of
    types to match against

    csubtype is an array that describes the collection subtype that has a list
    of subtypes to match against

    mvalue is an array that describes the list of collection values to match
    against.

    FRESH is an array that tells you how far back to look.

    '''

    logger = logging.getLogger("generic_large_compare")

    # Create my Cursor
    cur = db_conn.cursor()

    results_dict = deepcopy(host_list_dict)

    # So First I want to take my list of hosts and turn it into a string
    host_ids_list = list()
    fail_hosts = list()
    success_hosts = list()
    exempt_hosts = list()

    for item in host_list_dict:
        # Conatins all the hosts that haven't failed yet
        # print(item)
        host_ids_list.append(item['host_id'])
        # Contains all the hosts

    # print("Massaging")
    massaged_ctype = []
    massaged_csubtype = []
    massaged_mvalue = []

    if type(ctype) is str:
        massaged_ctype.append(ctype)
    else:
        # It's a list
        massaged_ctype = ctype

    if type(csubtype) is str:
        massaged_csubtype.append(csubtype)
    else:
        massaged_csubtype = csubtype

    if type(mvalue) is str:
        massaged_mvalue.append(mvalue)
    else:
        massaged_mvalue = mvalue

    if len(massaged_ctype) != len(massaged_csubtype) \
            or len(massaged_mvalue) != len(massaged_csubtype):
        # Error
        raise Exception("Subtype Count Mismatch")
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!1
        # Add a Return Value
    else:
        # Everthing matches

        host_ids_string = ",".join(map(str, host_ids_list))

        for index_value in range(0, len(massaged_ctype)):

            comparison = []
            comparison.append(
                "select fk_host_id, collection_value from collection")
            comparison.append("where collection_type = '" +
                              str(massaged_ctype[index_value]) + "' ")
            comparison.append(" and collection_subtype = '" +
                              str(massaged_csubtype[index_value]) + "' ")
            comparison.append(" and fk_host_id in (" + host_ids_string + ")")
            comparison.append(
                " and last_update >= now() - INTERVAL " + str(FRESH) + " SECOND ")
            comparison.append(
                " group by fk_host_id order by last_update desc ;")

            comparison_query = " ".join(comparison)

            if len(host_ids_list) > 0:
                # print(comparison_query)
                try:
                    logger.debug(
                        "Comparison Query : {}".format(comparison_query))
                    cur.execute(comparison_query)
                except Exception as DB_Error:
                    logger.error(
                        "Unable to Do Database Query on Generic Large Compare.")
                    query_results_list = list()
                else:
                    if cur.rowcount:
                        query_results_list = cur.fetchall()
                    else:
                        # No Results
                        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                        query_results_list = []
            else:
                query_results_list = []

            # print(query_results_list)
            exempthost = list()
            passhost = list()
            failhost = list()

            try:

                if mtype == "is" or mtype == "aptis":
                    exempthost = [host for host in query_results_list
                                  if len(host[1]) <= 0]
                    # TODO Why the hell does is not work here but in does?
                    # Figure it out find the "best"
                    # Currently this will "overmatch". So if you have a match of bionical
                    # And the value is bionic it will match.
                    passhost = [host for host in query_results_list
                                if host[1] in str(massaged_mvalue[index_value])]
                    failhost = [host for host in query_results_list
                                if host not in exempthost and
                                host not in passhost]

                elif mtype == "match" or mtype == "aptmatch":
                    exempthost = [host for host in query_results_list
                                  if len(host[1]) <= 0]
                    passhost = [host for host in query_results_list
                                if re.search(massaged_mvalue[index_value],
                                             host[1]) != None]
                    failhost = [host for host in query_results_list
                                if host not in exempthost and
                                host not in passhost]

                elif mtype == "nematch":
                    exempthost = [host for host in query_results_list
                                  if len(host[1]) <= 0]
                    passhost = [host for host in query_results_list
                                if re.search(massaged_mvalue[index_value],
                                             host[1]) == None]
                    failhost = [host for host in query_results_list
                                if host not in exempthost and
                                host not in passhost]

                elif mtype == "aptge":

                    match_version = packaging.version.parse(
                        massaged_mvalue[index_value])

                    exempthost = list()
                    passhost = list()
                    failhost = list()

                    for host in query_results_list:

                        # This was broke out to make the version parsing done here more readable.
                        collected_version = packaging.version.parse(host[1])

                        if len(host[1]) <= 0:
                            exempthost.append(host)
                        elif collected_version >= match_version:
                            passhost.append(host)
                        else:
                            failhost.append(host)

                elif mtype == "gt":
                    exempthost = [host for host in query_results_list
                                  if len(host[1]) <= 0]
                    passhost = [host for host in query_results_list
                                if int(host[1]) > int(massaged_mvalue[index_value])]
                    failhost = [
                        host for host in query_results_list if host not in exempthost and host not in passhost]
                elif mtype == "lt":
                    exempthost = [
                        host for host in query_results_list if len(host[1]) <= 0]
                    passhost = [host for host in query_results_list if int(
                        host[1]) < int(massaged_mvalue[index_value])]
                    failhost = [
                        host for host in query_results_list if host not in exempthost and host not in passhost]
                elif mtype == "eq":
                    exempthost = [
                        host for host in query_results_list if len(host[1]) <= 0]
                    passhost = [host for host in query_results_list if int(
                        host[1]) == int(massaged_mvalue[index_value])]
                    failhost = [
                        host for host in query_results_list if host not in exempthost and host not in passhost]
            except Exception as comparisons_error:
                logger.error(
                    "Error doing Comparisons for generic_large_compare.")
                logger.debug(comparisons_error)

            # Temporary List of HostID's
            exempthostids = list()
            passhostids = list()
            failhostids = list()

            #print("Exempt:", exempthost)
            #print("PASS:", passhost)
            #print("FAIL:", failhost)

            try:
                for item in exempthost:
                    # Allow us to say that exemption means failure default is to not
                    #print("Debug exeptfail = ", str(exemptfail) )
                    if exemptfail == False:
                        #print("adding to exempt")
                        exempthostids.append(item[0])
                    else:
                        #print("adding to fail")
                        failhostids.append(item[0])

                for item in passhost:
                    passhostids.append(item[0])

                for item in failhost:
                    failhostids.append(item[0])
            except Exception as e:
                print("Error creating host id lists : ", e)

            # print(results_dict)
            for host in range(0, len(results_dict)):
                # Hydrate if missing
                # if "pfe" not in results_dict[host].keys() :
                #   results_dict[host]['pfe'] = str()
                #   results_dict[host]['pfevalue'] = str()
                # print(failhostids)
                # print(passhostids)
                # print(exempthostids)
                # print(results_dict)
                # print(host)

                try:
                    if "pfe" in results_dict[host].keys() and results_dict[host]['pfe'] == "fail":
                        # I've already failed so fuck you ( :) )
                        pass
                    elif results_dict[host]['host_id'] in failhostids:
                        # I've now failed so place this in the results This will overwrite any exempt or pass entries
                        tmploc = failhostids.index(
                            results_dict[host]['host_id'])
                        results_dict[host]['pfe'] = "fail"
                        results_dict[host]['pfevalue'] = failhost[tmploc][1]
                    elif results_dict[host]['host_id'] in passhostids:
                        # print("PASSED")
                        tmploc = passhostids.index(
                            results_dict[host]['host_id'])
                        results_dict[host]['pfe'] = "pass"
                        results_dict[host]['pfevalue'] = passhost[tmploc][1]
                    elif results_dict[host]['host_id'] in exempthostids:
                        tmploc = exempthostids.index(
                            results_dict[host]['host_id'])
                        results_dict[host]['pfe'] = "notafflicted"
                        results_dict[host]['pfevalue'] = passhost[tmploc][1]
                    else:
                        # Your not in any of the hosts
                        # Normally I do nothing, however if I have exemptfail on I want you to fail
                        # Because it means that you're not here and not being here is a failure.
                        #print("In the else, ", str(exemptfail), " with ", host)
                        if exemptfail == True:
                            # Exempt fail is on so this is a failed host
                            results_dict[host]['pfe'] = "fail"
                            results_dict[host]['pfevalue'] = "exemptfail is True"
                        else:
                            # Exempt fail is not on so do nothing
                            pass

                except Exception as e:
                    print("Error trying to match items relating to host ",
                          host, " : ", e)

    # Close the MySQL Cursor
    cur.close()

    return results_dict
