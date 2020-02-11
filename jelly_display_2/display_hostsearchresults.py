#!/usr/bin/env python3

'''
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import ast

import requests
from flask import current_app, Blueprint, g, request, jsonify, render_template, abort

import manoward

hostsearchresults = Blueprint('hostsearchresults', __name__)


@hostsearchresults.route("/hostsearchresults")
@hostsearchresults.route("/hostsearchresults/")
def display2_hostsearchresults():
    
    '''
    Display Hostsearchresults from a particular search
    '''
    

    args_def = {"ctype": {"req_type": str,
                          "default": None,
                          "required": False,
                          "sql_param": False,
                          "qdeparse": True}}

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_hosts_sql=True,
                                 include_coll_sql=True,
                                 include_exact=True)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    this_endpoint = "{}/hostsearch?{}".format(g.config_items["v2api"]["root"],
                                              args["qdeparsed_string"])

    this_private_endpoint = g.HTTPENDPOINT + this_endpoint

    api_good = True

    try:
        tr = requests.get(this_private_endpoint)
        content_object = tr.json()
    except Exception as api_error:
        error_dict["Error Getting Endpoint"] = "Error getting endpoint: {}".format(
            api_error)
        api_good = False
    else:
        meta_dict["Endpoint"] = content_object["links"]["self"]

    if api_good:
        # Use my Template
        return render_template('display_V2/hostsearchresults.html', content=content_object, meta=meta_dict)
    else:
        return render_template('error.html', error=error_dict)
