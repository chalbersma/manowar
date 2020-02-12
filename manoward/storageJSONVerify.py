#! /usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# Parsing Argument
import argparse
# System Operations
import sys
# Import
import json
# Import
import os

# Schema Parser
import jsonschema


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # -h help
    # -s Audit Definitions (Required)
    # -j JSON File
    parser.add_argument(
        "-j", "--json", help="JSON File to Validate", required="TRUE")

    args = parser.parse_args()

    schema_file = args.schema
    json_file = args.json


def storageJSONVerify(json_file):
    '''
    Using the jsonschema file specified check the json bits for compliance
    '''

    has_passed = True
    message = "No Failures Detected"

    if isinstance(json_file, dict):
        # Treat this as the dict itself
        this_json = json_file
    else:
        try:
            with open(json_file, "r") as this_json_file:
                this_json = json.load(this_json_file)
        except ValueError as err:
            msg = "Error in the Format of your JSON File " + err
            return (False, msg)

    if isinstance(this_json, dict) is False:
        has_passed = False
        message = "Incorrect type of Data"

    if has_passed is True:
        # Required Key Checks
        required_keys = ["resource", "partition", "service", "region", "accountid",
                         "collection_hostname", "pop", "srvtype", "status", "uber_id"]
        required_int_keys = ["collection_timestamp"]
        required_dict_keys = ["collection_data"]
        collection_data_keys = ["host_host"]

        missing_keys = [mkey for mkey in [*required_keys, *required_int_keys,
                                          *required_dict_keys] if mkey not in this_json.keys()]

        missing_coll_keys = [mcollkey for mcollkey in collection_data_keys if mcollkey not in this_json.get(
            "collection_data", dict()).keys()]

        if len(missing_keys) > 0:
            has_passed = False
            message = "Missing Keys {}".format(",".join(missing_keys))

        elif len(missing_coll_keys) > 0:
            has_passed = False
            message = "Missing Collection Keys {}".format(
                ",".join(missing_coll_keys))

    return (has_passed, message)


if __name__ == "__main__":
    # "We're going to run the main stuff
    result = storageJSONVerify(schema_file, json_file)

    print(result)
