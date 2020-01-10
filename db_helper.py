#!/usr/bin/env python3

'''
db_helper.py

Provides common db functions for the project to standardize capabilities.
Idea is that you get a config that looks like (with an optional prefix)

dbhostname: hostname
dbport: port
dbuser: user
dbpassword: password
dbname: db
autocommit: bool
charset: string (default: utf8)


'''

import pymysql
import pyjq
import logging

def get_conn(config, prefix=None, tojq=None, **kwargs):

    # Given a Config Dictionary with an optional prefix and tojq
    # Pull the Data Out and Connect to the Database

    logger = logging.getLogger("db_helper.py")

    if isinstance(config, dict) is False:
        raise TypeError("config is not a dictionary")

    dbconfig = None

    if tojq is not None and isinstance(tojq, str):

        try:
            dbconfig = pyjq.first(tojq, config)
        except Exception as jq_error:
            logger.error("Unable to find config at jq rule : {}".format(tojq))
            logger.info("Error : {}".format(jq_error))

            raise jq_error
        else:
            logger.debug("Successfully tojq'ed this configuration.")
    else:
        dbconfig = config

    if isinstance(dbconfig, dict) is False:
        logger.error("DBConfig isn't here!")
        raise TypeError("Problem reading Database Information")

    pymysql_args = {"host" : dbconfig["{}dbhostname".format(prefix)],
                    "port" : int(dbconfig["{}dbport".format(prefix)]),
                    "user" : dbconfig["{}dbusername".format(prefix)],
                    "password" : dbconfig["{}dbpassword".format(prefix)],
                    "database" : dbconfig["{}dbdb".format(prefix)],
                    "autocommit" : dbconfig.get("{}autocommit".format(prefix), kwargs.get("ac_def", True)),
                    "charset" : dbconfig.get("{}charset".format(prefix), kwargs.get("char_def", "utf8mb4"))}

    if dbconfig.get("{}ssl", False) is True:
        pymysql_args["ssl"] = dict()

        ca = dbconfig.get("{}dbsslca".format(prefix), None)
        capath = dbconfig.get("{}dbsslcapath".format(prefix), None)
        cert = dbconfig.get("{}dbsslcert".format(prefix), None)
        key = dbconfig.get("{}dbsslkey".format(prefix), None)
        cipher = dbconfig.get("{}dbsslcipher".format(prefix), None)

        if ca is not None:
            pymysql_args["ssl"]["ca"] = ca
        if capath is not None:
            pymysql_args["ssl"]["capath"] = capath
        if cert is not None:
            pymysql_args["ssl"]["capath"] = cert
        if key is not None:
            pymysql_args["ssl"]["capath"] = key
        if cipher is not None:
            pymysql_args["ssl"]["capath"] = cipher

    try:

        db_conn = pymysql.connect(**pymysql_args)

        logger.info("Connected to {user}@{host}:{port}/{database}".format(**pymysql_args))

    except Exception as connection_error:
        logger.warning("Connection Failed to {user}@{host}:{port}/{database}".format(**pymysql_args))
        logger.debug("Error {}".format(connection_error))

        raise connection_error

    return db_conn
