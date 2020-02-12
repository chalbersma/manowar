#!/usr/bin/env python3

"""
Copyright 2020, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
"""


import json
import ast

from flask import current_app, Blueprint, g, request, jsonify, render_template
import requests


dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/dashboard")
@dashboard.route("/dashboard/")
@dashboard.route("/dashboard/<int:cust_dash_id>")
@dashboard.route("/dashboard/<int:cust_dash_id>/")
def display2_dashboard(cust_dash_id=None):
    
    '''
    Reworked but displays the old fashion dashboard
    '''

    argument_error = False
    meta_dict = dict()
    error_dict = dict()

    main_endpoint = "{}/dashboard/".format(g.config_items["v2api"]["root"])
    if cust_dash_id is None:
        this_endpoint = main_endpoint
    else:
        # Custom Dashbaord
        this_endpoint = main_endpoint + str(cust_dash_id)
    this_private_endpoint = g.HTTPENDPOINT + this_endpoint

    api_error = False

    try:
        results = requests.get(this_private_endpoint).json()
    except Exception as e:
        error_dict["Error Getting Endpoint"] = "Error getting endpoint: " + \
            str(e)
        api_error = True
    else:
        results["meta"]["Endpoint"] = this_endpoint
        g.logger.debug(results)

    if api_error:
        return render_template("error.html", error=error_dict)
    else:
        return render_template("display_V2/dashboard2.html", data=results["data"],
                               meta=results["meta"], links=results["links"])
