#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import ast
import urllib

import requests
from flask import current_app, Blueprint, g, request, jsonify, render_template, abort

import manoward

mainfactor = Blueprint('mainfactor', __name__)


@mainfactor.route("/mainfactor")
@mainfactor.route("/mainfactor/")
@mainfactor.route("/mainfactor/<string:factor>")
@mainfactor.route("/mainfactor/<string:factor>/")
def display2_collatedresults(factor=None):
    
    '''
    Mainfactor I think this might be a dupe
    '''

    args_def = {"factor": {"req_type": str,
                           "default": factor,
                           "required": True,
                           "qdeparse": True,
                           "enum": ("pop", "srvtype")}
                }

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_hosts_sql=True,
                                 include_exact=True)

    meta_dict = dict()
    #request_data = list()
    #links_dict = dict()
    error_dict = dict()

    argument_error = False
    query_string_bits = dict()

    this_endpoint = "{}/factorlist/?{}".format(g.config_items["v2api"]["root"],
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

        return render_template('display_V2/mainfactor.html',
                               content=content_object,
                               meta=meta_dict,
                               mainfactor=args["factor"])
    else:

        return render_template('error.html', error=error_dict)
