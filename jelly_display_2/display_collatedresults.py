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

collatedresults = Blueprint('collatedresults', __name__)


@collatedresults.route("/collatedresults")
@collatedresults.route("/collatedresults/")
@collatedresults.route("/collatedresults/<string:collatedType>")
@collatedresults.route("/collatedresults/<string:collatedType>/")
def display2_collatedresults(collatedType=False):
    '''
    Displays results from the audits_by_blah tables
    '''

    args_def = {"collatedType": {"req_type": str,
                                 "default": collatedType,
                                 "required": True,
                                 "enum": ("pop", "srvtype", "acoll")},
                "auditID": {"req_type": int,
                            "required": False,
                            "default": None,
                            "qdeparse": True},
                "typefilter": {"req_type": str,
                               "default": None,
                               "required": False,
                               "qdeparse": True}
                }

    args = manoward.process_args(args_def,
                                 request.args)

    meta_dict = dict()
    #request_data = list()
    #links_dict = dict()
    error_dict = dict()

    this_endpoint = "{}/collated/{}?{}".format(g.config_items["v2api"]["root"],
                                               collatedType,
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
        return render_template('display_V2/collatedresults.html',
                               content=content_object,
                               meta=meta_dict,
                               collatedType=collatedType,
                               typefilter=args["typefilter"])
    else:

        return render_template('error.html', error=error_dict)
