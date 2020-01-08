#!/usr/bin/env python3

'''
Configuration of API Users
'''

import os
import os.path
import logging

from configparser import ConfigParser

from yoyo import step

__depends__ = {"20200107_01_Gv0ql-initialize"}

# Permissions as they "should" be
_table_defs = {"manowar2.*" : {"api" : ["select"]},
               "manowar2.apiUsers": {"api" : ["insert", "update", "select", "delete"]},
               "manowar2.apiActiveTokens": {"api" : ["insert", "update", "select", "delete"]},
               "manowar2.custdashboard": {"api" : ["insert", "update", "select", "delete"]},
               "manowar2.custdashboardmembers": {"api" : ["insert", "update", "select", "delete"]},
               "manowar2.hosts": {"api" : ["insert", "update", "select", "delete"],
                                  "store" : ["insert", "update", "select", "delete"],
                                  "analyze" : ["select"]
                                 },
               "manowar2.collection": {"api" : ["insert", "update", "select", "delete"],
                                       "store" : ["insert", "update", "select", "delete"],
                                       "analyze" : ["select"]
                                      },
               "manowar2.collection_archive": {"analyze" : ["insert", "update", "select", "delete"],
                                               "store" : ["insert", "update", "select", "delete"]
                                              },
               "manowar2.audits_by_acoll_archive": {"analyze" : ["insert", "update", "select", "delete"],
                                                    "store" : ["insert", "update", "select", "delete"]
                                                   },
               "manowar2.sapiActiveHosts": {"api" : ["insert", "update", "select", "delete"],
                                            "store" : ["insert", "update", "select", "delete"]
                                           },
               "manowar2.ip_intel": {"api" : ["insert", "update", "select", "delete"]},
               "manowar2.audits": {"analyze" : ["insert", "update", "select", "delete"]},
               "manowar2.audits_by_host": {"analyze" : ["insert", "update", "select", "delete"]},
               "manowar2.audits_by_pop": {"analyze" : ["insert", "update", "select", "delete"]},
               "manowar2.audits_by_srvtype": {"analyze" : ["insert", "update", "select", "delete"]},
               "manowar2.audits_by_acoll": {"analyze" : ["insert", "update", "select", "delete"]}
              }


# Manowar API User manowar_api
# Lets find the yoyo.ini file

logger = logging.getLogger("yoyo-credentials Step")

logger.info("Finding Configuration File yoyo.ini")

do_api_attempt = True
config_file = None

# User Data
username = None
hostmask = None
req_enc = None
password = None

steps = list()

for default_file in ("../yoyo.ini", "./yoyo.ini"):
    if os.path.isfile(default_file) and os.access(default_file, os.R_OK):
        logger.debug("Using Default File : {}".format(default_file))
        config_file = default_file
        break

if config_file is None:
    logger.warning("Yoyo applied without a configuration file not attempting to update credential stuff.")
    raise ValueError("No yoyo configuration file given.")
else:
    # Load Configuration
    try:
        # Read Our INI with our data collection rules
        config = ConfigParser()
        config.read(config_file)
    except Exception as general_config_error:
        logger.warning("Couldn't read configuration file {} properly. Not doing api credential stuff.")
        raise general_config_error
    else:
        # DB Config Items
        yoyo_config = dict(config._sections)

        for user_type in ["api", "store", "analyze"]:

            if yoyo_config.get("manowar", dict()).get("{}_password".format(user_type), None) is  None:
                # We not doing it
                do_api_attempt = False
            else:
                username = yoyo_config.get("manowar", dict()).get("{}_username".format(user_type), None)
                hostmask = yoyo_config.get("manowar", dict()).get("{}_hostmask".format(user_type), None)
                password = yoyo_config.get("manowar", dict()).get("{}_password".format(user_type), None)

                req_enc = yoyo_config.get("manowar", dict()).get("req_enc", "SSL")


                this_u = '"{0}"@"{1}"'.format(username, hostmask)

                steps.append(step("create or replace user {0} identified by \"{1}\"".format(this_u,
                                                                                            password),
                                  "drop user {}".format(this_u)))

                if req_enc in ("SSL", "NONE", "X509"):
                    steps.append(step("alter user {0} REQUIRE {1}".format(this_u,
                                                                          req_enc)))
                else:
                    raise ValueError("req_enc not set to valid entry")

                # Now Add Permissions
                for this_table in _table_defs.keys():
                    if user_type in _table_defs[this_table].keys():
                        logger.info("Adding rights to {} for {}".format(this_table, user_type))

                        for right in _table_defs[this_table][user_type]:

                            steps.append(step("grant {} on {} to {}".format(right,
                                                                            this_table,
                                                                            this_u)))
                    else:
                        logger.debug("User {} Not granted access to {}".format(user_type, this_table))

    finally:
        pass
