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

import logging
import os

import pymysql
import pyjq
import yaml


def get_manoward(explicit_config=None, **kwargs):

    _manoward_defaults = ["/etc/manowar/manoward.yaml",
                          "./etc/manowar/manoward.yaml",
                          "/usr/local/etc/manowar/manoward.yaml"]
    
    '''
    Searches the filesystem for the correct manoward.yaml file and uses it.
    '''

    logger = logging.getLogger("manoward_configuration")

    if os.environ.get("TRAVIS", None) is not None:
        logger.info("In a Travis Build Add the Travis Paths to Configuration.")
        _manoward_defaults.append("../travis/artifacts/manoward.yaml")
        _manoward_defaults.append("./travis/artifacts/manoward.yaml")


    manoward_configs = None

    if isinstance(explicit_config, str):
        # Overwrite files with only this option.
        _manoward_defaults = [explicit_config]

    for default_file in _manoward_defaults:
        
        if os.path.isfile(default_file) is True and os.access(default_file, os.R_OK):
            logger.debug("Using Default File : {}".format(default_file))

            if kwargs.get("only_file", False) is False:
                # Process the config file and return results

                try:
                    with open(default_file, "r") as manoward_config_file:
                        manoward_configs = yaml.safe_load(manoward_config_file)

                except Exception as manoward_config_error:
                    logger.error("Unable to Read Manoward Configuration.")
                    logger.debug("Error : {}".format(manoward_config_error))

                    raise manoward_config_error
                else:
                    # I've now Got my Things
                    logger.info("Found and loaded manoward.yaml")
                    break
            else:
                # Return Just the filename
                manoward_configs = default_file

    if kwargs.get("no_config_okay", False) is True and manoward_configs is None:
        raise ValueError("No Manowar Configuration Found.")

    return manoward_configs


def get_conn(config, prefix=None, tojq=None, **kwargs):

    '''
    Returns a DB Cursors (with pymysql) that supports all of the
    hotness
    '''

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
            pymysql_args["ssl"]["cert"] = cert
        if key is not None:
            pymysql_args["ssl"]["key"] = key
        if cipher is not None:
            pymysql_args["ssl"]["cipher"] = cipher

    try:

        db_conn = pymysql.connect(**pymysql_args)

        logger.debug("Connected to {user}@{host}:{port}/{database}".format(**pymysql_args))

    except Exception as connection_error:
        logger.warning("Connection Failed to {user}@{host}:{port}/{database}".format(**pymysql_args))
        logger.debug("Error {}".format(connection_error))

        raise connection_error

    return db_conn
