#!/usr/bin/env python3

# Sting Cell
# The part of the oral arm of a jellyfish. Sounds better than oral arm.
# This is the client we've build/building that can go on boxes and communicate
# State Back to the jellyfish storage api (SAPI)
from configparser import ConfigParser
import argparse
import ast
import requests
import sys
import logging
import socket
# Subprocess Currently Needed
import subprocess # nosec
import json
import socket
import time
import os
import ipaddress
import yaml
import logging
import logging.handlers
import pprint

#
# Process
# 1. Grab Configs
# 1. Grab Collection Configuration
# 1. Do Collection
# 1. Submit Results
#
#

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="Stingcell Config File (Default /etc/stingcell/stingcell.ini)", default="/etc/stingcell/stingcell.ini")
    parser.add_argument("-p", "--print", help="Print stingcell json to stdout in addition to sending it along.", action='store_true')
    parser.add_argument("-n", "--noupload", help="Do not upload results to endoint.", action='store_true')
    parser.add_argument("-v", "--verbose", action='append_const', help="Turn on Verbosity", const=1, default=[])
    parser.add_argument("-l", "--logfile", help="Logfile to Store output in.", default=False)
    parser._optionals.title = "DESCRIPTION "

    # Parser Args
    args = parser.parse_args()

    CONFIG=args.config

    LOGFILE=args.logfile
    VERBOSE = len(args.verbose)

    FORMAT="%(levelname)s %(module)s P%(process)d T%(thread)d %(message)s"

    if VERBOSE == 0 :
        # Standard Error Logging
        logging.basicConfig(level=logging.ERROR,
                            format=FORMAT)

    elif VERBOSE >= 1 :
        if VERBOSE == 1:

            # Standard Debug Logging
            logging.basicConfig(level=logging.INFO,
                                format=FORMAT)

            # Turn down logging to Warning for these
            logging.getLogger("urllib3").setLevel(logging.WARNING)
            logging.getLogger("pika").setLevel(logging.WARNING)
            logging.getLogger("paramiko").setLevel(logging.WARNING)
            logging.getLogger("urllib3").setLevel(logging.WARNING)


        if VERBOSE >= 2 :
            logging.basicConfig(level=logging.DEBUG,
                                format=FORMAT)


    logger = logging.getLogger("stingcell.py")
    logger.info("Welcome to Stincell")

    if LOGFILE is not False:
        handler = logging.handlers.RotatingFileHandler(LOGFILE, when="d", interval=1, backupCount=14)
        logger.addHandler(handler)
    else:
        rsyslog_handler = logging.handlers.SysLogHandler(address="/dev/log")
        logger.addHandler(rsyslog_handler)



    if args.print:
        PRINT=True
    else:
        PRINT=False

    if args.noupload:
        NOUPLOAD = True
    else:
        NOUPLOAD = False


def local_ipintel(config_items=False, verbose=False, hostname=False, collections=dict()):


    # See if my Config says collect IP Intelligence
    dointel = config_items["ipintel"].get("dointel", "True")

    print(dointel)

    found_intel = list()

    if dointel :
        # Get Local Addresses
        ipa_object = socket.getaddrinfo(hostname, None)

        print("ipa_object", ipa_object)

        ipv4 = list()
        ipv6 = list()

        for group in ipa_object :
            this_unvalidated_ip = group[4][0]
            print(this_unvalidated_ip)

            PRIVATE_NETWORKS = [ ipaddress.ip_network("127.0.0.0/8"),
                                 ipaddress.ip_network("10.0.0.0/8"),
                                 ipaddress.ip_network("172.16.0.0/12"),
                                 ipaddress.ip_network("192.168.0.0/16"),
                                 ipaddress.ip_network("fd00::/8") ]


            isipv4=False
            isipv6=False

            try:
                validated_ipv4 = socket.inet_pton(socket.AF_INET, this_unvalidated_ip)
                isipv4 = True
            except OSError :
                # IPV4 Validation Failed, Try IPV6
                try:
                    validated_ipv6 = socket.inet_pton(socket.AF_INET6, this_unvalidated_ip)
                    isipv6 = True
                except OSError :
                    pass
            finally:
                # After this checks let's see what showed up
                if isipv4 or isipv6 :
                    # On or the other was true let's see if it's a private address
                    this_ip = ipaddress.ip_address(this_unvalidated_ip)

                    print(this_ip)

                    is_private = False
                    for priv_net in PRIVATE_NETWORKS :
                        if this_ip in priv_net :
                            # This is a private ip
                            print(this_ip, "Failed private network test")
                            is_private = True
                            break
                        else :
                            print(this_ip, "not in network", priv_net)

                    if is_private == False :
                        # It's not a private IP so add it to the intel report
                        if isipv4 :
                            ipv4.append(this_unvalidated_ip)
                        elif isipv6 :
                            ipv6.append(this_unvalidated_ip)

        unduped_ipv4 = list(set(ipv4))
        unduped_ipv6 = list(set(ipv6))

        print(unduped_ipv4, unduped_ipv6)

        this_intel = dict()
        this_intel["host4"] = unduped_ipv4
        this_intel["host6"] = unduped_ipv6

        for thing in ["host4", "host6"] :
            for ip in this_intel[thing] :
                this_report = { "iptype" : thing , \
                                 "ip" : ip }

                found_intel.append(this_report)

        # Now find collected intel based on configuration
        for this_intel_config in config_items["ipintel"].get("collectedintel", list() ) :
            this_ctype = this_intel_config["collection_type"]
            this_inteltype = this_intel_config["inteltype"]
            if this_ctype in collections.keys() :
                # There is a collection named that let's cycle throught hem
                for potential_intel in collections[this_ctype].keys() :
                    this_unvalidated_ip = collections[this_ctype][potential_intel]

                    # Now attempt to validate this ip
                    try:
                        validated_ip  = ipaddress.ip_address(this_unvalidated_ip)
                    except ValueError as valerr :
                        # Ignore this entry
                        pass
                    else :
                        # Was valid make a report
                        this_report = { "iptype" : this_inteltype, "ip" : validated_ip }
                        found_intel.append(this_report)

    else :
        pass

    return found_intel

def stingcell(configfile=False, verbose=False, ignoreupload=False, LOGGER=False) :

    FNULL = open(os.devnull, 'w')

    if os.path.isfile(configfile) == False :
        # This is an error
        LOGGER.error("Config File {} not found. Exiting".format(configfile))
        sys.exit('Error: Config File {} not found'.format(configfile))

    # Step 1 Base Configuration Grab Configuration
    with open(configfile) as configuration_file:
        try:
            config_items = yaml.load(configuration_file)
        except yaml.YAMLError as yaml_error:
            LOGGER.error("Configuration file parse failure.")
            LOGGER.debug("Error {}".format(yaml_error))
            sys.exit('Bad configuration file {}'.format(yaml_error))
        else:
            pass

    # Step 2 Grab Collection Configuration
    collection_configuration_file = config_items["stingcell"]["collection_config_file"]

    with open(collection_configuration_file, "r") as coll_conf_file:
        # Parse Yaml File
        try:
            to_collect_items = yaml.load(coll_conf_file)
        except yaml.YAMLError as yaml_error:
            LOGGER.error("Unable to read collection configuration file {} with error : \n{}".format(collection_configuration_file, str(yaml_error)))
            sys.exit("Bad Collection Configuration File {}".format(collection_config_file))
        else:
            pass

    # Local Collections
    if config_items["stingcell"].get("local_collections", False) == True :
        # I want Local Collections
        collections_d_dir = config_items["stingcell"].get("local_collections_location", "/etc/stingcell/collections.d")
        collections_files = list()
        for (dirpath, dirnames, filenames) in os.walk(collections_d_dir) :
            for singlefile in filenames :
                onefile = dirpath + "/" +  singlefile
                #print(singlefile.find(".ini", -4))
                if singlefile.find(".ini", -4) > 0 :
                    # File ends with .ini Last 4 chars
                    collections_files.append(onefile)

        for collection_file in collections_files :
            try:
                # Read Our INI with our data collection rules
                this_local_coll = yaml.load(collection_file)
            except Exception as e: # pylint: disable=broad-except, invalid-name
                sys.stderr.write("Bad collection configuration file {} cannot parse: {}".format(collection_file, str(e)))
            else:
                # I've read and parsed this file let's add the things
                for this_new_coll_key in this_local_coll.get("collections", {}).keys():
                    to_collect_items[this_new_coll_key]=this_local_coll[this_new_coll_key]

    # Step 3 Collect Results

    results_dictionary = dict()
    results_dictionary["collection_data"] = dict()

    # Collect Configurables

    for collection in to_collect_items["collections"].keys() :


        is_multi = to_collect_items["collections"][collection]["multi"]
        coll_command = to_collect_items["collections"][collection]["collection"]
        timeout = to_collect_items["collections"][collection].get("timeout", config_items["stingcell"]["default_collection_timeout"])

        LOGGER.debug("Running collection : '{}' ({}, {}) with command {} ".format(collection, \
                                                                                is_multi, timeout, \
                                                                                coll_command))

        parsed_data = dict()

        try:
            # Bandit doesn't like this and that makes perfect sense. This is essentially vulnerable to a bad config file
            # Doing something bad. We mitigate this by running stingcell (and collections in general) as an unprivildged
            # user. Additionally config files are controlled via SVN/Salt or queried directly from Jellyfish (where it's
            # also controlled by SVN/Salt.
            #
            # Running configurable commands is the core of how Jellyfish collects data.
            raw_output = subprocess.check_output(coll_command, shell=True, executable="/bin/bash", timeout=int(timeout), stderr=FNULL) # nosec
        except subprocess.CalledProcessError as e :
            error_dict = { "collection_failed" : "Error running command in collection : " + str(collection) + " error : " + str(e) }
            LOGGER.warn(error_dict["collection_failed"])
            parsed_data = error_dict
        except subprocess.TimeoutExpired as e :
            error_dict = { "collection_timenout" : "Error running command in collection : " + str(collection) + " timeout at " + str(timeout) + " seconds." }
            LOGGER.warn(error_dict["collection_timeout"])
            parsed_data = error_dict
        else :
            string_output = raw_output.decode()

            if len(string_output) == 0 :
                # No String Ouptut
                parsed_data = { "default" : "no_output" }
                LOGGER.warn("Collection {} returned no output".format(collection))
            else :

                if is_multi is True:
                    # Multi Line Output to Record
                    multiD_dict = dict()

                    for item in string_output.splitlines() :
                        multiD_dict[item.split()[0]] = " ".join(item.split()[1:])

                    parsed_data = multiD_dict

                else :
                    # Not a Multi Line Output to Record
                    dat_collection = { "default" : string_output.strip() }
                    parsed_data = dat_collection

        results_dictionary["collection_data"][collection] = parsed_data

    # Collect Host Stuff

    # Found Stuff
    socket_hostname = socket.gethostname()

    # Found Pop
    try:
        # Needed for core functionality, low Severity so Noseccing
        raw_found_pop = subprocess.check_output("/EdgeCast/base/getSrvinfo pop", shell=True, executable="/bin/bash", timeout=5, stderr=FNULL) # nosec
    except Exception as e :
        found_pop = "N/A"
    else :
        found_pop = raw_found_pop.decode()

    # Found Srvtype
    try:
        # Same as Pop
        raw_found_srvtype = subprocess.check_output("/EdgeCast/base/getSrvinfo srvtype", shell=True, executable="/bin/bash", timeout=5, stderr=FNULL) # nosec
    except Exception as e :
        found_srvtype = "N/A"
    else :
        found_srvtype = raw_found_srvtype.decode()

    # Found Status
    try:
        # Same as Pop & Srvtype
        raw_found_status = subprocess.check_output("/EdgeCast/base/getSrvinfo my-uber-status", shell=True, executable="/bin/bash", timeout=5, stderr=FNULL) # nosec
    except Exception as e :
        # Assume it's prod
        found_status = "prod"
    else :
        found_status = raw_found_status.decode()

    multi_hostname = config_items["hostinfo"].get("hostname", socket_hostname)
    multi_pop = config_items["hostinfo"].get("pop", found_pop)
    multi_srvtype = config_items["hostinfo"].get("srvtype", found_srvtype)
    multi_status = config_items["hostinfo"].get("status", found_status)
    # No way to find uber id on host (yet)
    multi_uberid = config_items["hostinfo"].get("uberid", "N/A")

    collection_status = "STINGCELL"
    connection_string = "Via StingCell"

    # Add host_host data
    results_dictionary["collection_data"]["host_host"] = { "HOSTNAME" : multi_hostname , "POP" : multi_pop , "SRVTYPE" : multi_srvtype, "UBERID" : multi_uberid, "STATUS" : multi_status }

    results_dictionary["ip_intel"] = local_ipintel(config_items=config_items, verbose=verbose, hostname=multi_hostname, collections=results_dictionary["collection_data"] )

    # Add Base Data
    results_dictionary["collection_hostname"] = multi_hostname
    results_dictionary["collection_status"] = collection_status
    results_dictionary["collection_timestamp"] = int(time.time())
    results_dictionary["connection_string"] = connection_string
    results_dictionary["pop"] = multi_pop
    results_dictionary["srvtype"] = multi_srvtype
    results_dictionary["status"] = multi_status
    results_dictionary["uber_id"] = multi_uberid

    # Step 4 Stick that Shit in the API
    request_headers = { "Authorization" : config_items["sapi"].get("sapi_username", "nobody") + ":" + config_items["sapi"].get("sapi_token", "nothing") ,
                                                "Content-Type" : "application/json" }

    collection_data_json = json.dumps(results_dictionary)

    url = config_items["sapi"]["sapi_endpoint"] + "sapi/puthostjson/"

    if ignoreupload == True:
        # Don't do the upload just return the data
        pass
    else:
        # The default, do the needful baby!
        if verbose == True :
            LOGGER.debug("Collections Finished, Uploading Data to : {} as user {} ".format(url, config_items["sapi"].get("sapi_username", "nobody") ) )

        try :
            this_request = requests.post(url, data=collection_data_json, headers=request_headers)
        except Exception as e :
            print("Error posting data back to SAPI {}".format(e))
        else :
            response_code = this_request.status_code
            if response_code == 200 :
                if verbose == True :
                    LOGGER.debug("VERBOSE: Data Successfully Posted to : {}".format(url))
            else :
                LOGGER.warning("Data posted to : {} but returned status code {} ".format(url, response_code))

    return collection_data_json



if __name__ == "__main__":
    collection_data = stingcell(configfile=CONFIG, verbose=VERBOSE, ignoreupload=NOUPLOAD, LOGGER=logging)

    if PRINT == True :
        sys.stdout.write(collection_data)
