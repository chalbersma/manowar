#!/usr/bin/env python3

# Salt Cell

import yaml
import jq
import requests
import sys
import argparse
import logging
import json

#import salt.config
#import salt.client

from saltcell.clientcollector import Host

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
    parser._optionals.title = "DESCRIPTION "

    # Parser Args
    args = parser.parse_args()

    VERBOSE = len(args.verbose)

    if VERBOSE == 0 :
        logging.basicConfig(level=logging.ERROR)

    elif VERBOSE == 1 :
        logging.basicConfig(level=logging.WARNING)

    elif VERBOSE == 2 :
        logging.basicConfig(level=logging.INFO)

    else:
        logging.basicConfig(level=logging.DEBUG)

    logger = logging.getLogger("saltcell.py")

    logger.info("Welcome to Saltcell")

    with open(args.config, "r") as config_file:
        try:
            configs = yaml.load(config_file)
        except yaml.YAMLError as parse_error:
            print("Unable to parse file {} with error : \n {}".format(args.config, parse_error))
            sys.exit(1)

    if args.print:
        PRINT=True
    else:
        PRINT=False

    if args.noupload:
        NOUPLOAD = True
    else:
        NOUPLOAD = False


def docoll(config_items=False, noupload=False) :

    logger = logging.getLogger("saltcell.docoll")


    '''
    Do the Collection
    '''

    # Step 2 Grab Collection Configuration
    collection_configuration_file = config_items["stingcell"]["collection_config_file"]

    this_host = Host(minion_file=config_items["salt"].get("minion_file", "minion"), \
                     base_config_file=config_items["stingcell"]["collection_config_file"], \
                     local_cols=(config_items["stingcell"].get("local_collections", False), \
                                 config_items["stingcell"].get("local_collections_location", "/etc/stingcell/collections.d")),
                     host_configs=config_items["hostinfo"],
                     ipintel_configs=config_items["ipintel"])

    results = this_host.todict()

    print(json.dumps(results))


    # Collect Host Stuff
    '''

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
    '''

    return



if __name__ == "__main__":
    collection_data = docoll(config_items=configs)

    if PRINT == True :
        sys.stdout.write(collection_data)
