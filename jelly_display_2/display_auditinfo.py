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

auditinfo = Blueprint('auditinfo', __name__)


@auditinfo.route("/auditinfo")
@auditinfo.route("/auditinfo/")
@auditinfo.route("/auditinfo/<int:audit_id>")
@auditinfo.route("/auditinfo/<int:audit_id>/")
def display2_auditinfo(audit_id="0"):
    
    '''
    Driver for non-bucket audit info. Loads the data from the database

    Someday will load the bucketdata too.
    '''

    args_def = {"audit_id": {"req_type": int,
                             "default": audit_id,
                             "positive": True,
                             "required": True}}

    args = manoward.process_args(args_def,
                                 request.args)

    meta_dict = dict()

    error_dict = dict()

    this_endpoint = "{}/auditinfo/{}?{}".format(g.config_items["v2api"]["root"],
                                                args["audit_id"],
                                                args["qdeparsed_string"])

    this_private_endpoint = "{}{}".format(g.HTTPENDPOINT, this_endpoint)

    api_good = True

    try:
        tr = requests.get(this_private_endpoint)
        content_object = tr.json()
    except Exception as api_error:
        error_dict["Error Getting Endpoint"] = "Error getting endpoint: {}".format(
            api_error)
        api_good = False
    else:
        g.logger.info(content_object)
        meta_dict["Endpoint"] = content_object["links"]["self"]

    if api_good:
        return render_template('display_V2/auditinfo.html', audit_id=audit_id, content=content_object, meta=meta_dict)
    else:
        return render_template('error.html', error=error_dict)
