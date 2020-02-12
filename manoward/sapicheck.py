#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from colorama import Fore, Back, Style
from configparser import ConfigParser
import pymysql
import logging

import manoward


def grab_all_sapi(config_items):

    logger = logging.getLogger("sapicheck")

    all_hosts = list()

    db_conn = manoward.get_conn(
        config_items, prefix="store_", tojq=".database", ac_def=True)
    db_cur = db_conn.cursor(pymysql.cursors.DictCursor)

    all_sapi_hosts_sql = "select hostname from sapiActiveHosts where last_updated >= (now() - INTERVAL 3 DAY) "

    try:
        db_cur.execute(all_sapi_hosts_sql)

        results = db_cur.fetchall()
    except Exception as sapi_query_error:

        logger.warning("{}{}Unable to Grab all SAPI Hosts.{}".format(Back.WHITE,
                                                                     Fore.RED,
                                                                     Style.RESET_ALL))
        logger.debug("Error : {}".format(sapi_query_error))

    else:

        for host in results:
            # Pop host onto array
            all_hosts.append(host["hostname"])

    # Retun the hosts I've found, if non will return an empty list.
    finally:

        db_cur.close()
        db_conn.close()

    return all_hosts
