#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import ast

import requests
from flask import current_app, Blueprint, g, request, jsonify, render_template, abort

import manoward

display_collected_values = Blueprint('display2_collected_values', __name__)


@display_collected_values.route("/collected/values")
@display_collected_values.route("/collected/values/")
@display_collected_values.route("/collected/values/<string:ctype>", methods=['GET'])
@display_collected_values.route("/collected/values/<string:ctype>/", methods=['GET'])
def display2_collected_values(ctype=None):
    
    '''
    Display 2 Collected Values
    '''

    args_def = {"ctype": {"req_type": str,
                          "default": ctype,
                          "required": True,
                          "qdeparse": False}}

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_hosts_sql=True,
                                 include_coll_sql=True,
                                 include_exact=True)

    meta_dict = dict()

    meta_dict["ctype"] = args["ctype"]

    if args.get("csubtype") is None:
        meta_dict["csubtype"] = "*"
    else:
        meta_dict["csubtype"] = args["csubtype"]

    meta_dict["common_qdeparsed_string"] = args["common_qdeparsed_string"]

    request_data = list()
    links_dict = dict()
    error_dict = dict()

    this_endpoint = "{}/collected/values/{}?{}".format(g.config_items["v2api"]["root"],
                                                       args["ctype"],
                                                       args["common_qdeparsed_string"])

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
        return render_template('display_V2/collected_values.html', content=content_object, meta=meta_dict)
    else:
        return render_template('error.html', error=error_dict)
