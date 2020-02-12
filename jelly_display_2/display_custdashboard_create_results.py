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

display_custdashboard_create_results = Blueprint(
    'display2_custdashboard_create_results', __name__)


@display_custdashboard_create_results.route("/custdashboard/create_results", methods=['GET', 'POST'])
@display_custdashboard_create_results.route("/custdashboard/create_results/", methods=['GET', 'POST'])
def display2_custdashboard_create_results(dashboard_name=None, dashboard_description=None):
    
    '''
    Display the Results from a Cust Dashboard Creation
    
    TODO Modernize
    '''

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    query_string_bits = dict()

    if "dashboard_name" in request.args:
        dashboard_name = ast.literal_eval(request.args["dashboard_name"])
    elif "dashboard_name" in request.form:
        dashboard_name = str(request.form["dashboard_name"])
    else:
        argument_error = True
        error_dict["No Dashboard Name"] = True

    if "dashboard_description" in request.args:
        dashboard_description = ast.literal_eval(
            request.args["dashboard_description"])
    elif "dashboard_description" in request.form:
        dashboard_description = str(request.form["dashboard_description"])
    else:
        argument_error = True
        error_dict["No Dashboard Description"] = True

    # Gen query string
    if argument_error == False:
        try:

            query_string_bits["dashboard_name"] = "'{}'".format(dashboard_name)
            query_string_bits["dashboard_description"] = "'''{}'''".format(
                dashboard_description)

            print(query_string_bits)

            query_string = urllib.parse.urlencode(query_string_bits)
            meta_dict["query_string"] = query_string
            this_endpoint = g.config_items["v2api"]["root"] + \
                "/custdashboard/create/?" + query_string
            this_private_endpoint = g.HTTPENDPOINT + this_endpoint

            print(this_endpoint)
            print(this_private_endpoint)
        except Exception as e:
            error_dict["query_string_error"] = "Error generating query string: " + \
                str(e)
            argument_error = True
        else:
            meta_dict["Endpoint"] = str(
                g.config_items["v2api"]["preroot"]) + this_endpoint

    api_error = False

    if argument_error == False:
        try:
            content = requests.get(this_private_endpoint).content
        except Exception as e:
            error_dict["Error Getting Endpoint"] = "Error getting endpoint: " + \
                str(e)
            api_error = True
        else:
            try:
                content_string = content.decode("utf-8")
                content_object = json.loads(content_string)
            except Exception as e:
                api_error = True
                error_dict["Error Rendering API Content"] = "Error reading data from endpoint: " + \
                    str(e)
    else:
        api_error = True

    if api_error:
        return render_template('error.html', error=error_dict)
    else:
        return render_template('display_V2/custdashboard_create_results.html', content=content_object, meta=meta_dict)
