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


def process_ip_intel(config_dict=False, ip=False, iptype=False, host_id=False, multireport=False, **kwargs):
    '''
    Does the needful on IP Intelligence
    #TODO Allow direct storage for zero API storage activities
    '''

    mylogger = logging.getLogger("process_ip_intel.py")

    request_headers = dict()
    request_headers["Content-Type"] = "application/json"
    query_arguments = dict()

    if config_dict is False:
        raise Exception("No Config Specified")

    if config_dict["ip_intel"].get("use_auth", False) is True:

        # Use an auth token when you make the query
        request_headers["Authorization"] = "{}:{}".format(self.config_dict["ip_intel"].get("intel_username", "nobody"),
                                                          self.config_dict["ip_intel"].get("intel_token", "nothing"))
    # Always send hostname
    query_arguments["hostid"] = host_id

    report_url = config_dict["ip_intel"].get(
        "report_url", "https://robot.manowar.local/v2/ip/report/")

    response_codes = list()

    mylogger.debug(multireport)
    if multireport is False:
        reports = [{"ip": ip, "iptype": iptype}]
    else:
        reports = multireport

    for this_report in reports:
        mylogger.debug(query_arguments)
        mylogger.debug(this_report)
        query_arguments = {**query_arguments, **this_report}

        try:
            mylogger.debug("Reporting {} {} on host {}".format(
                this_report["ip"], this_report["iptype"], host_id))

            this_request = requests.get(
                report_url, headers=request_headers, params=query_arguments)
        except Exception as reporting_error:
            mylogger.error("Error Reporting Intel for hostid {} with error {}".format(
                host_id, str(reporting_error)))
            response_codes.append(-1)
        else:
            if this_request.status_code == 200:
                mylogger.info(
                    "Reported IP Intelligence for hostid {} succeeded".format(host_id))
            elif this_request.status_code == 202:
                mylogger.info(
                    "Reported IP Intelligence was successful but ignored by System.".format(host_id))
            else:
                mylogger.error("Reporting IP Intelligence for hostname {} failed. (Error Code: {})".format(
                    host_id, this_request.status_code))

            response_codes.append(this_request.status_code)

    return response_codes
