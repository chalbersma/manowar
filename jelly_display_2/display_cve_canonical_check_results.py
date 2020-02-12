#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import ast
import urllib

from flask import current_app, Blueprint, g, request, jsonify, render_template
import requests

display_cve_canonical_check_results = Blueprint(
    'display2_cve_canonical_check_results', __name__)


@display_cve_canonical_check_results.route("/cve_canonical_check_results")
@display_cve_canonical_check_results.route("/cve_canonical_check_results/")
def display2_cve_canonical_check_results(exact=False, hostname=False, hoststatus=False, pop=False, srvtype=False, cve_name=False):
    
    '''
    Runs an Adhoc analysis based on a single CVE
    '''

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    query_args = dict()

    # Grab Values

    if "cve_name" in request.args:
        try:
            cve_name = ast.literal_eval(request.args["cve_name"])
            query_args["cve_name"] = "'{}'".format(str(cve_name))
        except Exception as e:
            error_dict["cve_name_read_error"] = "Error parsing hostname " + \
                str(e)
            argument_error = True

    if "hostname" in request.args:
        try:
            hostname = ast.literal_eval(request.args["hostname"])
            query_args["hostname"] = "'{}'".format(str(hostname))
        except Exception as e:
            error_dict["hostname_read_error"] = "Error parsing hostname " + \
                str(e)
            argument_error = True

    if "hoststatus" in request.args:
        try:
            hoststatus = ast.literal_eval(request.args["hoststatus"])
            query_args["hoststatus"] = "'{}'".format(str(hoststatus))
        except Exception as e:
            error_dict["hoststatus_read_error"] = "Error parsing hoststatus " + \
                str(e)
            argument_error = True

    if "pop" in request.args:
        try:
            pop = ast.literal_eval(request.args["pop"])
            query_args["pop"] = "'{}'".format(str(pop))
        except Exception as e:
            error_dict["pop_read_error"] = "Error parsing pop " + str(e)
            argument_error = True

    if "srvtype" in request.args:
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
            query_args["srvtype"] = "'{}'".format(str(srvtype))
        except Exception as e:
            error_dict["srvtype_read_error"] = "Error parsing srvtype " + \
                str(e)
            argument_error = True

    if "exact" in request.args:
        try:
            exact = ast.literal_eval(request.args["exact"])
        except Exception as e:
            error_dict["hostname_read_error"] = "Error parsing hostname " + \
                str(e)
            argument_error = True
        else:
            if exact == True:
                query_args["exact"] = "True"

    if argument_error == False:
        try:
            cve_check_local_query = g.config_items["v2api"]["root"] + \
                "/cve/canonical_check/?"

            query_string = urllib.parse.urlencode(query_args)
            meta_dict["args"] = query_args

            cve_check_private = "{}{}{}".format(
                g.HTTPENDPOINT, cve_check_local_query, query_string)

            this_endpoint = cve_check_local_query + query_string

            this_private_endpoint = g.HTTPENDPOINT + this_endpoint

        except Exception as e:
            error_dict["query_string_error"] = "Error generating query string: " + \
                str(e)
            argument_error = True
        else:
            meta_dict["Endpoint"] = str(
                g.config_items["v2api"]["preroot"]) + this_endpoint

    # Grab Endpoint
    api_error = False

    try:
        content = requests.get(this_private_endpoint)
        content_json = content.json()
    except Exception as e:
        error_dict["Error Getting Endpoint"] = "Error getting endpoint: " + \
            str(e)
        api_error = True
    else:
        if "errors" in content_json.keys():
            api_error = True
            error_dict["api_error_found"] = "Found errors in api call."
            error_dict["error"] = content_json["errors"]
        else:
            # We Gud!
            pass

    if api_error:
        return render_template('error.html', error=error_dict)
        # Use my Template
    else:
        return render_template('display_V2/cve_canonical_check_results.html', content=content_json, meta=meta_dict)
