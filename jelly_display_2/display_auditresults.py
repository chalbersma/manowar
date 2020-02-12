#!/usr/bin/env python3

'''Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import requests

from flask import current_app, Blueprint, g, request, jsonify, render_template, abort

import manoward

auditresults = Blueprint('auditresults', __name__)


@auditresults.route("/auditresults")
@auditresults.route("/auditresults/")
@auditresults.route("/auditresults/<int:audit_id>")
@auditresults.route("/auditresults/<int:audit_id>/")
def display2_auditresults(audit_id=0):
    
    '''
    Display Audit Results for This system
    '''

    args_def = {"audit_id": {"req_type": int,
                             "default": audit_id,
                             "positive": True,
                             "required": True}}

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_hosts_sql=True,
                                 include_ar_sql=True,
                                 include_exact=True,)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    g.logger.debug(args)

    this_endpoint = "{}/auditresults/{}/?{}".format(g.config_items["v2api"]["root"],
                                                    args["audit_id"],
                                                    args["qdeparsed_string"])

    this_private_endpoint = "{}{}".format(g.HTTPENDPOINT, this_endpoint)

    api_good = True

    g.logger.debug(this_private_endpoint)

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
        return render_template('display_V2/auditresults.html', audit_id=args["audit_id"], content=content_object, meta=meta_dict)
    else:

        return render_template('error.html', error=error_dict)
