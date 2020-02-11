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

display_subtypes_filtered = Blueprint('display2_subtypes_filtered', __name__)


@display_subtypes_filtered.route("/collected/subtypes_filtered", methods=['GET'])
@display_subtypes_filtered.route("/collected/subtypes_filtered/", methods=['GET'])
@display_subtypes_filtered.route("/collected/subtypes_filtered/<string:ctype>", methods=['GET'])
@display_subtypes_filtered.route("/collected/subtypes_filtered/<string:ctype>/", methods=['GET'])
def display2_subtypes_filtered(ctype=None):
    
    '''
    Display A Filtered Subtypes for a particular Collection req_type
    '''

    args_def = {"ctype": {"req_type": str,
                          "default": ctype,
                          "required": True,
                          "qdeparse": False},
                "usevalue": {"req_type": str,
                             "default": None,
                             "required": False,
                             "qdeparse": True,
                             "enum": ("true", "false")}
                }

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_hosts_sql=True,
                                 include_coll_sql=True,
                                 include_exact=True)

    this_endpoint = "{}/collected/subtypes_filtered/{}?{}".format(g.config_items["v2api"]["root"],
                                                                  args["ctype"],
                                                                  args["qdeparsed_string"])

    meta_dict = dict()

    # For use in Template
    meta_dict["ctype"] = args["ctype"]
    meta_dict["usevalue"] = args["usevalue"]
    meta_dict["common_qdeparsed_string"] = args["common_qdeparsed_string"]

    error_dict = dict()

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
        return render_template('display_V2/collected_subtypes_filtered.html', content=content_object, meta=meta_dict, usevalue=args["usevalue"])
    else:
        return render_template('error.html', error=error_dict)
