#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

#from configparser import ConfigParser
from colorama import Fore, Back, Style
import time
import argparse
import ast
import logging

import pymysql

import manoward

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", help="JSON Config File with our Storage Info", required=True)
    parser.add_argument("-V", "--verbose", action="store_true",
                        help="Enable Verbose Mode")
    parser._optionals.title = "DESCRIPTION "

    # Parser Args
    args = parser.parse_args()

    # Grab Variables
    CONFIG = args.config
    VERBOSE = args.verbose


def archive_collections(CONFIG, age=90):

    logger = logging.getLogger("collection_archive")

    # Parse my General Configuration
    if isinstance(CONFIG, dict):
        config_items = CONFIG
    elif isinstance(CONFIG, str):
        config_items = manoward.get_manoward(explicit_config=CONFIG)
    else:
        raise TypeError("No Configuration Given.")

    db_conn = manoward.get_conn(
        config_items, prefix="store_", tojq=".database", ac_def=True)

    cur = db_conn.cursor()

    archive_ts = int(time.time())

    logger.debug("Archive ts: {}".format(archive_ts))

    populate_archive_sql = '''REPLACE INTO collection_archive
                                SELECT * FROM collection
                                WHERE
                                last_update < FROM_UNIXTIME(%s) -  interval %s DAY ; '''

    remove_overachieving_sql = '''DELETE FROM collection
                                    WHERE last_update < FROM_UNIXTIME(%s) - interval %s DAY ; '''

    archive_args = [archive_ts, age]

    copy_action = manoward.run_query(cur,
                                     populate_archive_sql,
                                     args=archive_args,
                                     require_results=False,
                                     do_abort=False)

    if copy_action["has_error"] is True:
        logger.error("{}Had an Error When Running Archive. Ignoring Delete{}".format(
            Fore.RED, Style.RESET_ALL))
    else:
        # Run Delete
        logger.info("Archive Worked Swimmingly. Let's Go Ahead and Delete.")

        delete_action = manoward.run_query(cur,
                                           remove_overachieving_sql,
                                           args=archive_args,
                                           require_results=False,
                                           do_abort=False)

        if delete_action["has_error"] is True:
            logger.error("{}Error when deleting the Excess.{}".format(
                Fore.RED, Style.RESET_ALL))
        else:
            logger.info("{}Collection Table Archived {}".format(
                Fore.GREEN, Style.RESET_ALL))


if __name__ == "__main__":
    archive_collections(CONFIG)
