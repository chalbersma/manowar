#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import ast

import requests
from flask import current_app, Blueprint, g, request, jsonify, render_template

display_custdashboard_modify = Blueprint(
    'display2_custdashboard_modify', __name__)


@display_custdashboard_modify.route("/custdashboard/modfiy")
@display_custdashboard_modify.route("/custdashboard/modfiy/")
@display_custdashboard_modify.route("/custdashboard/modify/<int:dash_id>")
@display_custdashboard_modify.route("/custdashboard/modify/<int:dash_id>/")
def display2_custdashboard_modify(dash_id=False):
    
    '''
    Displays the Custdashboard modify Interface
    
    TODO Modernize
    '''

    argument_error = False
    api_error = False
    query_string_bits = list()
    error_dict = dict()

    avail_audits = list()
    current_audits = list()

    if "dash_id" in request.args:
        try:
            dash_id = ast.literal_eval(request.args["dash_id"])
        except Exception as e:
            argument_error = True
            error_dict["dash_id_parse_fail"] = "Failed to Parse Dash_id"

    if type(dash_id) is int:
        pass
    else:
        argument_error = True
        error_dict["dash_id_incorrect"] = "Either not a valid dash_id or not an integer"

    if argument_error == False:
        try:
            this_auditlist_endpoint = "/v2/auditlist/?"
            this_custdashboard_endpoint = "/v2/custdashboard/dashboard/{}/?".format(
                str(dash_id))
            this_custdashboard_general_endpoint = "/v2/custdashboard/list/{}/?".format(
                str(dash_id))
            this_private_auditlist_endpoint = g.HTTPENDPOINT + this_auditlist_endpoint
            this_private_custdashboard_endpoint = g.HTTPENDPOINT + this_custdashboard_endpoint
            this_private_custdashboard_general_endpoint = g.HTTPENDPOINT + \
                this_custdashboard_general_endpoint
        except Exception as e:
            error_dict["query_string_error"] = "Error generating self api: " + \
                str(e)
            argument_error = True
        else:

            try:
                audits_list_text = requests.get(
                    this_private_auditlist_endpoint).text
                custdashboard_list_text = requests.get(
                    this_private_custdashboard_endpoint).text
                custdashboard_general_text = requests.get(
                    this_private_custdashboard_general_endpoint).text

                custdashboard_list = json.loads(custdashboard_list_text)
                audits_list = json.loads(audits_list_text)
                custdashboard_general = json.loads(custdashboard_general_text)

            except Exception as e:
                error_dict["Error Getting Endpoint"] = "Error getting endpoint: " + \
                    str(e)
                api_error = True
            else:

                if "data" in custdashboard_list.keys():
                    current_audits_id_validation = [
                        caudit["attributes"]["fk_audits_id"] for caudit in custdashboard_list["data"]]
                    current_audits = custdashboard_list["data"]
                else:
                    # Make Empty
                    current_audits_id_validation = list()
                    current_audits = list()

                avail_audits = [audit for audit in audits_list["data"]
                                if audit["id"] not in current_audits_id_validation]

    if argument_error == False and api_error == False:
        return render_template('display_V2/custdashboard_modify.html', current_audits=current_audits, avail_audits=avail_audits, dash_id=dash_id, dashboard=custdashboard_general)
    else:
        print(error_dict)
        return render_template('error.html', error=error_dict)
