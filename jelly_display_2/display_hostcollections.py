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

hostcollections = Blueprint('hostcollections', __name__)


@hostcollections.route("/hostcollections")
@hostcollections.route("/hostcollections/")
@hostcollections.route("/hostcollections/<int:host_id>")
@hostcollections.route("/hostcollections/<int:host_id>/")
def display2_hostcollections(host_id=0):
    
    '''
    Displya my Host's Collections
    '''

    args_def = {"hostid": {"req_type": int,
                           "default": host_id,
                           "required": True,
                           "positive": True},
                "ctype": {"req_type": str,
                          "default": None,
                          "required": False,
                          "qdeparse": True}
                }

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_coll_sql=True,
                                 include_exact=True)

    meta_dict = dict()

    meta_dict["hostid"] = args["hostid"]

    request_data = list()
    links_dict = dict()
    error_dict = dict()

    this_endpoint = "{}/hostcollections/{}?{}".format(g.config_items["v2api"]["root"],
                                                      args["hostid"],
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
        return render_template('display_V2/hostcollections.html',
                               host_id=args["hostid"],
                               content=content_object,
                               meta=meta_dict)
    else:
        return render_template('error.html', error=error_dict)
