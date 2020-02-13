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
import urllib.parse

import pyjq
import yaml
from flask import abort

import pymysql

_hosts_sql = {"hostname": {"req_type": str,
                           "default": None,
                           "required": False,
                           "sql_param": True,
                           "sql_clause": "hosts.hostname REGEXP %s",
                           "sql_exact_clause": "hosts.hostname = %s",
                           "qdeparse": True},
              "status": {"req_type": str,
                         "default": None,
                         "required": False,
                         "sql_param": True,
                         "sql_clause": "hosts.hoststatus REGEXP %s",
                         "sql_exact_clause": "hosts.hoststatus = %s",
                         "qdeparse": True},
              "pop": {"req_type": str,
                      "default": None,
                      "required": False,
                      "sql_param": True,
                      "sql_clause": "hosts.pop REGEXP %s",
                      "sql_exact_clause": "hosts.pop = %s",
                      "qdeparse": True},
              "srvtype": {"req_type": str,
                          "default": None,
                          "required": False,
                          "sql_param": True,
                          "sql_clause": "hosts.srvtype REGEXP %s",
                          "sql_exact_clause": "hosts.srvtype = %s",
                          "qdeparse": True},
              "resource" : {"req_type": str,
                          "default": None,
                          "required": False,
                          "sql_param": True,
                          "sql_clause": "hosts.mresource REGEXP %s",
                          "sql_exact_clause": "hosts.mresource = %s",
                          "qdeparse": True},
              "partition" : {"req_type": str,
                             "default": None,
                             "required": False,
                             "sql_param": True,
                             "sql_clause": "hosts.mpartition REGEXP %s",
                             "sql_exact_clause": "hosts.mpartititon = %s",
                             "qdeparse": True},
              "service" : {"req_type": str,
                             "default": None,
                             "required": False,
                             "sql_param": True,
                             "sql_clause": "hosts.mservice REGEXP %s",
                             "sql_exact_clause": "hosts.mservice = %s",
                             "qdeparse": True},
              "accountid" : {"req_type": str,
                           "default": None,
                           "required": False,
                           "sql_param": True,
                           "sql_clause": "hosts.maccountid REGEXP %s",
                           "sql_exact_clause": "hosts.maccountid = %s",
                           "qdeparse": True},
              "mownbase" : {"req_type": str,
                             "default": None,
                             "required": False,
                             "sql_param": True,
                             "sql_clause": "hosts.mownbase REGEXP %s",
                             "sql_exact_clause": "hosts.mownbase = %s",
                             "qdeparse": True},
              "mownfull" : {"req_type": str,
                             "default": None,
                             "required": False,
                             "sql_param": True,
                             "sql_clause": "hosts.mownfull REGEXP %s",
                             "sql_exact_clause": "hosts.mownfull = %s"},
              "tagged" : {"req_type": str,
                         "default": None,
                         "required": False,
                         "sql_param": True,
                         "sql_clause": "JSON_EXISTS(hosts.mowntags, %s)",
                         "qdeparse": True},
              "taggedtrue" : {"req_type": str,
                             "default": None,
                             "required": False,
                             "sql_param": True,
                             "sql_clause": "JSON_EXTRACT(hosts.mowntags, %s) = true",
                             "qdeparse": True}}

_ar_filters = {"bucket": {"req_type": str,
                          "default": None,
                          "required": False,
                          "sql_param": True,
                          "sql_clause": "audits_by_host.bucket REGEXP %s",
                          "sql_exact_clause": "audits_by_host.bucket = %s",
                          "qdeparse": True},
               "auditResult": {"req_type": str,
                               "default": None,
                               "required": False,
                               "sql_param": True,
                               "sql_clause": "audits_by_host.audit_result REGEXP %s",
                               "sql_exact_clause": "audits_by_host.audit_result = %s",
                               "qdeparse": True},
               "auditResultText": {"req_type": str,
                                   "default": None,
                                   "required": False,
                                   "sql_param": True,
                                   "sql_clause": "audits_by_host.audit_result_text REGEXP %s",
                                   "sql_exact_clause": "audits_by_host.audit_result_text = %s",
                                   "qdeparse": True}}

_exact_filter = {"exact": {"req_type": str,
                           "default": None,
                           "required": False,
                           "sql_param": False,
                           "qdeparse": True,
                           "enum": ("true", "false")}}

_collection_filters = {"value": {"req_type": str,
                                 "default": None,
                                 "required": False,
                                 "sql_param": True,
                                 "sql_clause": "collection.collection_value REGEXP %s",
                                 "sql_exact_clause": "collection.collection_value = %s",
                                 "qdeparse": True},
                       "csubtype": {"req_type": str,
                                    "default": None,
                                    "required": False,
                                    "sql_param": True,
                                    "sql_clause": "collection.collection_subtype REGEXP %s",
                                    "sql_exact_clause": "collection.collection_subtype = %s",
                                    "qdeparse": True}}


def process_args(definitions, this_request_args, **kwargs):
    '''
    Process the Arguments And Return a Dictionary with the Results
    '''

    logger = logging.getLogger("db_helper.process_args")

    return_dict = dict()

    return_dict["args_clause"] = list()
    return_dict["args_clause_args"] = list()
    return_dict["qdeparsed"] = dict()
    return_dict["qdeparsed_string"] = str()

    return_dict["all_common_keys"] = list()
    return_dict["common_qdeparsed_string"] = str()

    if kwargs.get("include_hosts_sql", False) is True:
        logger.info("Including Default Host Arguments with SQL Limitations")
        definitions = {**_hosts_sql, **definitions}

        return_dict["all_common_keys"].extend(list(_hosts_sql.keys()))

    if kwargs.get("include_ar_sql", False) is True:
        logger.info("Including Audit Result Host Arguments with Limitations.")
        definitions = {**_ar_filters, **definitions}

        return_dict["all_common_keys"].extend(list(_ar_filters.keys()))

    if kwargs.get("include_coll_sql", False) is True:
        logger.info("Including Default Collections SQL Limitations")
        definitions = {**_collection_filters, **definitions}

        return_dict["all_common_keys"].extend(list(_collection_filters.keys()))

    if kwargs.get("include_exact", False) is True:
        logger.info("Including Exact Host Arguments.")
        definitions = {**_exact_filter, **definitions}

        return_dict["all_common_keys"].extend(list(_exact_filter.keys()))

    if kwargs.get("coll_lulimit", None) is not None and isinstance(kwargs["coll_lulimit"], int):
        # Collections Specific
        return_dict["args_clause"].append(
            "collection.last_update >= FROM_UNIXTIME(%s)")
        return_dict["args_clause_args"].append(kwargs["coll_lulimit"])

    if kwargs.get("abh_limit", None) is not None and isinstance(kwargs["abh_limit"], int):
        return_dict["args_clause"].append(
            "audits_by_host.last_audit >= FROM_UNIXTIME(%s)")
        return_dict["args_clause_args"].append(kwargs["abh_limit"])

    if kwargs.get("lulimit", None) is not None and isinstance(kwargs["lulimit"], int):
        # Naked
        return_dict["args_clause"].append(
            "hosts.last_update >= FROM_UNIXTIME(%s)")
        return_dict["args_clause_args"].append(kwargs["lulimit"])

    for this_var, this_def in definitions.items():

        traget = dict()

        if "req_type" in this_def.keys():
            traget["type"] = this_def["req_type"]

        try:
            return_dict[this_var] = this_request_args.get(this_var,
                                                          default=this_def.get(
                                                              "default", None),
                                                          **traget)
        except Exception as request_get_error:
            logger.error(
                "Error getting variable {} from Query Args".format(this_var))
            logger.debug(request_get_error)
            abort(500)
        else:
            if this_def.get("required", True) is True and return_dict[this_var] is None:
                logger.error(
                    "Variable {} Required on API Endpoint but Not Given".format(this_var))
                abort(417)
            if return_dict[this_var] is None and this_var in this_request_args:
                logger.error("Variable given in Query Args Makes No Sense")
                abort(415)

            if return_dict[this_var] is not None and this_def.get("positive", False) is True and this_def.get("req_type", "unknown") is int:

                logger.debug(this_var)
                logger.debug(return_dict[this_var])

                if return_dict[this_var] <= 0:
                    logger.error(
                        "Variable {} Requested a Postive Integer. Did not Recieve".format(this_var))
                    abort(415)

            if isinstance(this_def.get("enum", None), (list, tuple)) and this_def.get("req_type", None) is str:

                match = [matched for matched in this_def["enum"]
                         if matched == return_dict[this_var]]

                if len(match) == 0:
                    if this_def.get("required", False) is True:
                        logger.error("Value {} Isn't in Known Enum List : {}".format(return_dict[this_var],
                                                                                     this_def["enum"]))
                        abort(415)

        finally:
            # Process Where Args and Such Where I have a Result
            if return_dict[this_var] is not None:
                # SQL Paramaters
                if this_def.get("sql_param", False) and isinstance(this_def.get("sql_clause", None), str):
                    return_dict["args_clause_args"].append(
                        return_dict[this_var])

                    if return_dict.get("exact", None) != "true":
                        # Use Default SQL Clause
                        return_dict["args_clause"].append(
                            this_def["sql_clause"])
                    else:
                        # If I have a sql_exact_clause use that (if not use the sql_clause)
                        return_dict["args_clause"].append(this_def.get(
                            "sql_exact_clause", this_def["sql_clause"]))

                    if this_def.get("sql_param_count", 1) > 1:
                        # Multiple Adds
                        for add in range(1, this_def["sql_param_count"]):
                            return_dict["args_clause_args"].append(
                                return_dict[this_var])

                elif this_def.get("sql_param", False) is True:
                    logger.error(
                        "Half SQL Definition Given, Missing SQL Clause")
                    abort(415)
                elif isinstance(this_def.get("sql_clause", None), str):
                    logger.error(
                        "Half SQL Definition Given, Missing SQL Param True")
                    abort(415)

                # Query Arg Parsing
                if this_def.get("qdeparse", False) is True:
                    return_dict["qdeparsed"][this_var] = return_dict[this_var]

    if len(return_dict["qdeparsed"]) > 0:
        return_dict["qdeparsed_string"] = urllib.parse.urlencode(
            return_dict["qdeparsed"])

    if len(return_dict["all_common_keys"]) > 0:
        return_dict["common_qdeparsed"] = {
            k: return_dict[k] for k in return_dict["all_common_keys"] if return_dict[k] is not None}
        return_dict["common_qdeparsed_string"] = urllib.parse.urlencode(
            return_dict["common_qdeparsed"])

    return return_dict


def run_query(db_cur, query, args=list(), **kwargs):
    '''
    Run the Database Query given using the PYMYSQL data we know about
    Return the data (assuming Dictionary unless mentioned)
    '''

    logger = logging.getLogger("db_helper.run_query")

    has_error = False

    results = {"has_error": False,
               "data": None}

    try:
        if kwargs.get("many", False) is True:
            debug_query = db_cur.mogrify(query, args[0])
            logger.debug("Debug Query 0 of {} : \n{}".format(len(args),
                                                             debug_query))
            query_results = list()
            for this_args in args:
                db_cur.execute(query, this_args)
                query_results.append(db_cur.fetchone())

        else:
            debug_query = db_cur.mogrify(query, args)
            logger.debug("Debug Query : \n{}".format(debug_query))
            db_cur.execute(query, args)

    except pymysql.IntegrityError as integrity_error:
        logger.error("Integrity Error on Query :{}".format(integrity_error))
        has_error = True
        if kwargs.get("do_abort", False) is True:
            abort(500)

    except pymysql.ProgrammingError as programming_error:
        logger.error(
            "Programming Error on Query :{}".format(programming_error))
        has_error = True
        if kwargs.get("do_abort", False) is True:
            abort(500)

    except pymysql.DataError as data_error:
        logger.error("Data Error on Query :{}".format(data_error))
        has_error = True
        if kwargs.get("do_abort", False) is True:
            abort(500)

    except pymysql.NotSupportedError as not_supported:
        logger.error("Not Supported Error on Query :{}".format(not_supported))
        has_error = True
        if kwargs.get("do_abort", False) is True:
            abort(500)

    except pymysql.OperationalError as operational_error:
        logger.error(
            "Operational Error on Query :{}".format(operational_error))
        has_error = True
        if kwargs.get("do_abort", False) is True:
            abort(500)

    except Exception as general_error:
        logger.error("General Error on Query :{}".format(general_error))
        has_error = True
        if kwargs.get("do_abort", False) is True:
            abort(500)
    else:

        # Successful Query
        if kwargs.get("many", False) is True:
            # Collection Inline
            pass
        else:
            if kwargs.get("one", False) is True:
                query_results = db_cur.fetchone()
            else:
                query_results = db_cur.fetchall()

        if kwargs.get("require_results", False) is True:
            if query_results is None or len(query_results) == 0:
                logger.error("No Results when Results Required.")
                has_error = True
                if kwargs.get("do_abort", False) is True:
                    abort(404)

        results["data"] = query_results

    finally:

        results["has_error"] = has_error

    if kwargs.get("do_abort", False) is True and results["has_error"] is True:
        logger.error("Error while Abort Requested.")
        abort(500)

    return results


def get_manoward(explicit_config=None, **kwargs):
    '''
    Grab Manoward Configurations
    Searches the filesystem for the correct manoward.yaml file and uses it.
    '''

    _manoward_defaults = ["/etc/manowar/manoward.yaml",
                          "./etc/manowar/manoward.yaml",
                          "/usr/local/etc/manowar/manoward.yaml"]

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

    pymysql_args = {"host": dbconfig["{}dbhostname".format(prefix)],
                    "port": int(dbconfig["{}dbport".format(prefix)]),
                    "user": dbconfig["{}dbusername".format(prefix)],
                    "password": dbconfig["{}dbpassword".format(prefix)],
                    "database": dbconfig["{}dbdb".format(prefix)],
                    "autocommit": dbconfig.get("{}autocommit".format(prefix), kwargs.get("ac_def", True)),
                    "charset": dbconfig.get("{}charset".format(prefix), kwargs.get("char_def", "utf8mb4"))}

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

        logger.debug(
            "Connected to {user}@{host}:{port}/{database}".format(**pymysql_args))

    except Exception as connection_error:
        logger.warning(
            "Connection Failed to {user}@{host}:{port}/{database}".format(**pymysql_args))
        logger.debug("Error {}".format(connection_error))

        raise connection_error

    return db_conn
