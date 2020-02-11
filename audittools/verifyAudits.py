#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# verifyAudits.py - Designed to verify that all of our audit files
# are good to go.


# Run through Analysis
import os
import json
import logging
import ast
import argparse
import sys

from time import time
from configparser import ConfigParser

import yaml


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("-a", "--auditdir", help="Directory that Contains the audits", required=True)
    parser.add_argument("-v", "--verbose", action='append_const', help="Turn on Verbosity", const=1, default=[])

    # Parser Args
    args = parser.parse_args()

    # Massage Configdir to not include trailing /
    if args.auditdir[-1] == "/":
        CONFIGDIR = args.auditdir[0:-1]
    else:
        CONFIGDIR = args.auditdir

    VERBOSE = len(args.verbose)

    if VERBOSE == 0:
        logging.basicConfig(level=logging.ERROR)
    elif VERBOSE == 1:
        logging.basicConfig(level=logging.WARNING)
    elif VERBOSE == 2:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)

    LOGGER = logging.getLogger("verifyAudits.py")

def walk_auditd_dir(configdirs):

    '''
    Walk the Auditd Dir and get all the valid types
    '''

    logger = logging.getLogger("verifyAudits.py:walk_auditd_dir")

    __acceptable_filename = [".ini", ".yaml", ".json"]

    auditfiles_found = list()

    if isinstance(configdirs, str):
        all_configdirs = [configdirs]
    elif isinstance(configdirs, (list, tuple)):
        all_configdirs = configdirs

    for configdir in all_configdirs:
        for (dirpath, dirnames, filenames) in os.walk(configdir):

            for singlefile in filenames:
                onefile = dirpath + "/" +  singlefile
                #print(singlefile.find(".ini", -4))
                added = False
                for filetype in __acceptable_filename:
                    if singlefile.endswith(filetype) is True:
                        # File ends with .ini Last 4 chars
                        auditfiles_found.append(onefile)
                        added = True

                if added is False:
                    logger.info("File {} Found in Audit Config Dir that's not being processed.".format(onefile))
                    logger.debug("Current Dir {}".format(dirnames))

    return auditfiles_found


def load_auditfile(auditfile):

    '''
    Loads a single auditfile with possibly more than one audit per file.
    '''

    logger = logging.getLogger("verifyAudits.py:load_auditfile")

    # Config Defaults For .ini file replacement

    this_time = int(time())
    back_week = this_time-604800
    back_month = this_time-2628000
    back_quarter = this_time-7844000
    back_year = this_time-31540000
    back_3_year = this_time-94610000
    time_defaults = {"now" : str(this_time),
                     "weekago" : str(back_week),
                     "monthago" : str(back_month),
                     "quarterago" : str(back_quarter),
                     "yearago" : str(back_year),
                     "threeyearago" : str(back_3_year)}

    audits = dict()

    logger.debug("Attempting to Load Audits from Auditfile : {}".format(auditfile))

    try:
        if os.path.isfile(auditfile):
            if auditfile.endswith(".yaml") is True:
                # YAML Parse
                with open(auditfile) as yaml_file:
                    this_audit_config = yaml.safe_load(yaml_file)
            elif auditfile.endswith(".json") is True:
                with open(auditfile) as json_file:
                    this_audit_config = json.load(json_file)
            elif auditfile.endswith(".ini", -4) is True:
                this_audit_config = ConfigParser(time_defaults)
                this_audit_config.read(auditfile)
            else:
                raise ValueError("Unknown File Type : {}".format(auditfile))
        else:
            raise NotFounFoundError("Unknown File : {}".format(auditfile))

    except Exception as parse_exception:
        # Error if Parse
        logger.error("File {} not parsed because of {}".format(auditfile, parse_exception))
    else:
        # It's good so toss that shit in

        if auditfile.endswith(".ini"):

            for section in this_audit_config:
                if section not in ["GLOBAL", "DEFAULT"]:
                    audits[section] = dict()

                    # Add Defaults Info
                    audits[section]["filename"] = auditfile

                    # Items this_audit_config
                    for item in this_audit_config[section]:
                        onelinethisstuff = "".join(this_audit_config[section][item].splitlines())
                        try:
                            if item == "vuln-long-description":
                                audits[section][item] = ast.literal_eval("'''{}'''".format(onelinethisstuff))
                            else:
                                audits[section][item] = ast.literal_eval(onelinethisstuff)
                        except Exception as ast_error:
                            logger.error("Verification ini style Failed. Use verifyAudits.py for more details")
                            logger.debug("INI Exception on AST Parsing {}:{} : {}".format(section, item, ast_error))

        else:
            for section in this_audit_config.keys():
                if isinstance(this_audit_config[section], dict):

                    # Add Default Filename and Data
                    audits[section] = {"filename" : auditfile, 
                                       **this_audit_config[section]}

    logger.info("File {} Returning {} Audits.".format(auditfile, len(audits.keys())))
    logger.debug("File {} Returning Audits {}".format(auditfile, ",".join(audits.keys())))

    return audits

def verifySingleAudit(auditfile):

    '''
    Verifies a Single Already Parsed Audit or Given Auditfile

    Utilizes Load Function for Loading a String.
    '''

    logger = logging.getLogger("verifyAudits.py:verifySingleAudit")

    field_strings = ["vuln-name", "vuln-short-description", "vuln-primary-link", "vuln-long-description"]
    field_ints = ["vuln-priority"]
    field_ints_optional = ["now", "monthago", "threeyearago", "quarterago", "weekago", "yearago", "auditts"]
    field_dicts = ["vuln-additional-links", "filters", "comparisons"]
    field_uncontrolled = ["filename", "jellyfishversion"]
    max_fields = field_strings + field_ints + field_dicts + field_uncontrolled + field_ints_optional
    required_fields = field_strings + field_ints + field_dicts

    fields_checked = []

    verified = True

    if isinstance(auditfile, str):
        this_audit_config = load_auditfile(auditfile)
        audit_file_name = auditfile
    elif isinstance(auditfile, dict):
        this_audit_config = auditfile
        audit_file_name = "digital"
    else:
        raise TypeError("Unkown Auditfile Type.")

    # Now let's do the Checks
    for section in this_audit_config.keys():
        # I let "Global or Default" fly right now
        if section not in ["GLOBAL", "DEFAULT"]:

            logger.debug("Validating Audit with Name {}".format(section))

            ##### Parse Check ########
            filter_object = dict()
            comparison_object = dict()

            for item in this_audit_config[section]:
                fields_checked.append(item)

                if item in field_strings:
                    if isinstance(this_audit_config[section][item], str) is False:
                        logger.error("Issue with file {} audit {} item {} Type is not string.".format(audit_file_name, section, item))
                        logger.debug("Type {} / Value {}".format(type(this_audit_config[section][item]), this_audit_config[section][item]))
                        verified = False
                elif item in field_ints:
                    if isinstance(this_audit_config[section][item], int) is False:
                        logger.error("Issue with file {} audit {} item {} Type is not int.".format(audit_file_name, section, item))
                        logger.debug("Type {} / Value {}".format(type(this_audit_config[section][item]), this_audit_config[section][item]))
                        verified = False
                elif item in field_dicts:
                    if isinstance(this_audit_config[section][item], dict) is False:
                        logger.error("Issue with file {} audit {} item {} Type is not dict.".format(audit_file_name, section, item))

                        logger.debug("Type {} / Value {}".format(type(this_audit_config[section][item]), this_audit_config[section][item]))
                        verified = False
                    if item == "filters":
                        filter_object = this_audit_config[section][item]
                    if item == "comparisons":
                        comparison_object = this_audit_config[section][item]
                elif item in field_uncontrolled:
                    # Uncontrolled Fields not Controlled
                    pass
                elif item in field_ints_optional:
                    if isinstance(this_audit_config[section][item], int) is False:
                        logger.error("Optional Field {} Defined but is not an Integer. Breaking.".format(item))
                        verified = False
                else:
                    # Auto Error unkown Field
                    logger.error("Issue with file {} audit {} item {} field is Unknown.".format(audit_file_name, section, item))
                    verified = False

            ## Compare buckets
            total_buckets_check = [bucket for bucket in comparison_object.keys()]

            if len(total_buckets_check) == 0:
                logger.error("Issue with file {} audit {} 0 Buckets Defined.".format(audit_file_name, section))
                logger.debug("No Buckets defined in Comparisons.")
                verified = False

            comparison_okay = [bucket for bucket in comparison_object.keys() if bucket not in filter_object.keys()]
            filter_okay = [bucket for bucket in comparison_object.keys() if bucket not in filter_object.keys()]

            if len(comparison_okay) > 0 or len(filter_okay) > 0:

                logger.error("Issue with file {} audit {} Mismatch on Filters/Buckets".format(audit_file_name, section))
                logger.debug("Bad filters = {}".format(" , ".join(filter_okay)))
                logger.debug("Bad Comparisons = {}".format(", ".join(comparison_okay)))

                verified = False

            ## Check Counts
            if len(fields_checked) > len(max_fields) or len(fields_checked) < len(required_fields):

                missing_fields = [field for field in all_fields if field not in required_fields]
                extra_fields = [field for field in fields_checked if field not in max_fields]

                logger.error("Issue with file {} audit {} has missing or extra fields.".format(audit_file_name, section))
                logger.debug("Extra Fields = {}".format(" , ".join(extra_fields)))
                logger.debug("Missing Fields = {}".format(" , ".join(missing_fields)))

                verified = False

    return verified

def verifyAudits(CONFIGDIR):

    '''
    Verify All the Audits in the Given Auditdir
    '''

    currently_verified = True

    # Grab all my Audits in CONFIGDIR Stuff
    auditfiles = walk_auditd_dir(CONFIGDIR)

    #audits=dict()
    for auditfile in auditfiles:
        if verifySingleAudit(auditfile) is False:
            currently_verified = True

    return currently_verified


if __name__ == "__main__":
    okay = verifyAudits(CONFIGDIR)

    if okay is True:
        LOGGER.info("Audits Okay")
        sys.exit(0)
    else:
        LOGGER.info("Audits checks Failed")
        sys.exit(1)
