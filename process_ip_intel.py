#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

Process IP Intelligence. Designed to be called by , "the thing" and
use the api to report data back.
'''

import requests
import logging
import json

def process_ip_intel(config_dict=False, ip=False, iptype=False, host=False, multireport=False, mylogger=False):

    if mylogger == False :
        # Setup a Default Logger
        FORMAT="%(levelname)s %(asctime)s %(name)s : %(message)s"
        logging.basicConfig(level=logging.ERROR, format=FORMAT)
        mylogger = logging.getLogger("process_ip_intel.py")

    request_headers = dict()
    query_arguments = dict()

    if config_dict == False :
        raise Exception("No Config Specified")

    if config_dict["ip_intel"].get("use_auth", False) == True :

        # Use an auth token when you make the query
        request_headers["Authorization"] =  "{}:{}".format(self.config_dict["ip_intel"].get("intel_username","nobody"),
                                                           self.config_dict["ip_intel"].get("intel_token","nothing")
                                                          )

    if (multireport is False and (ip is False or iptype is False)) or host is False:
        raise Exception("Incomplete Specification")

    if multireport is False:
        # Use the Given
        query_arguments["ip"] = "'{}'".format(str(ip))
        query_arguments["iptype"] = "'{}'".format(str(iptype))
    else :
        request_headers["Content-Type"] = "application/json"
        if isinstance(multireport, list):
            # multireport
            pass
        else :
            # Fail this
            mylogger.error("Error multireport incorrect type for host {}".format(host))

    # Always send hostname
    query_arguments["hostname"] = "'{}'".format(str(host))

    report_url = config_dict["ip_intel"].get("report_url", "https://robot.jellyfish.edgecast.com/v2/ip/report/")

    try:

        if multireport == False :
            # Do a Get
            this_request = requests.get(report_url, headers=request_headers, params=query_arguments)
        else :
            # Do a Post
            multireport_in_json = json.dumps(multireport)
            this_request = requests.post(report_url, headers=request_headers, params=query_arguments, data=multireport_in_json)

        mylogger.debug("Reporting Intel for hostname : {} ".format(str(host)))
    except Exception as e :
        # Do some error thing here.
        mylogger.error("Error Reporting Intel for hostname {} with error {}".format(str(host), str(e)))
        response_code = 0
    else :
        response_code = this_request.status_code

        if response_code == 200 :
            mylogger.info("Reported IP Intelligence for hostname {} succeeded".format(host))
        else :
            mylogger.error("Reporting IP Intelligence for hostname {} failed. (Error Code: {})".format(str(host), str(response_code)))

    return response_code
