#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import ast

import requests
from flask import current_app, Blueprint, g, request, jsonify, render_template

custdashboardlist = Blueprint('custdashboardlist', __name__)


@custdashboardlist.route("/custdashboardlist")
def display2_custdashboardlist():
    
    '''
    Lists Custom Dashboards in the System
    
    TODO Modernize
    '''

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    query_string_bits = list()

    if argument_error == False:
        try:
            this_endpoint = g.config_items["v2api"]["root"] + \
                "/custdashboard/list/"
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
        content = requests.get(this_private_endpoint).text
    except Exception as e:
        error_dict["Error Getting Endpoint"] = "Error getting endpoint: " + \
            str(e)
        api_error = True
    else:
        try:
            content_object = json.loads(content)
        except Exception as e:
            api_error = True
            error_dict["Error Rendering API Content"] = "Error reading data from endpoint: " + \
                str(e)

    if api_error:
        return render_template('error.html', error=error_dict)
        # Use my Template
    else:
        return render_template('display_V2/custdashboardlist.html', content=content_object, meta=meta_dict)
