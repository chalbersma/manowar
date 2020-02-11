#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/sapi/adduser endpoint. Designed to initiate a sapi API user.

```swagger-yaml
/custdashboard/create/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Creates a New Jellyfish2 Custom Audit.
    responses:
      200:
        description: OK
    tags:
      - dashboard
    parameters:
      - name: username
        x-astliteraleval: true
        in: query
        description: |
          Username that wants to be created.
        schema:
          type: string
        required: true
      - name: purpose
        x-astliteraleval: true
        in: query
        description: |
          Reason that user was created. Requires a ticket denoted in brackets.
        schema:
          type: string
        required: true
```

'''

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory
import json
import ast
import time
import os
import hashlib
import re
import manoward

custdashboard_create = Blueprint('api2_custdashboard_create', __name__)


@custdashboard_create.route("/custdashboard/create", methods=['GET', 'POST'])
@custdashboard_create.route("/custdashboard/create/", methods=['GET', 'POST'])
def api2_custdashboard_create(dashboard_name=None, dashboard_description=None):

    meta_dict = dict()
    request_data = dict()
    links_dict = dict()
    error_dict = dict()

    #
    # Don't allow local whitelist and api users to create dashboards.
    # Require an ldap user to create a new dashboard.
    #

    this_endpoint_restrictions = (
        ("conntype", "whitelist"), ("conntype", "robot"))
    this_endpoint_endorsements = (("conntype", "ldap"), )

    manoward.process_endorsements(endorsements=this_endpoint_endorsements,
                                  restrictions=this_endpoint_restrictions,
                                  session_endorsements=g.session_endorsements,
                                  session_restrictions=g.session_restrictions,
                                  ignore_abort=g.debug)

    do_query = True
    argument_error = False
    where_clauses = list()

    if "dashboard_name" in request.args:
        dashboard_name = ast.literal_eval(request.args["dashboard_name"])
    if "dashboard_description" in request.args:
        dashboard_description = ast.literal_eval(
            request.args["dashboard_description"])

    if dashboard_name == None or dashboard_description == None:
        error_dict["arg_error"] = "Need both a dashboard_name & dashboard_description"
        argument_error = True

    if type(dashboard_name) is not str or type(dashboard_description) is not str:
        error_dict["arg_pars_error"] = "Odd winds are blowing."

    username = g.USERNAME

    # Dashboard Validate
    if dashboard_name.isalpha() and dashboard_name.islower():
        # We've Validated
        pass
    else:
        argument_error = True
        error_dict["dashboard_name_error"] = "given dashbaord name needs to be lower case and all letters."

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 Custdashboard Create "
    meta_dict["status"] = "In Progress"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/sapi"

    requesttype = "custdashboard_create"

    insert_args = [username, dashboard_name, dashboard_description]
    insert_query = ''' insert into custdashboard ( owner, dashboard_name,
                                    dashboard_description ) VALUES ( %s , %s , %s )
                                    '''

    if do_query and argument_error == False:
        try:
            g.cur.execute(insert_query, insert_args)

            custdashid = g.cur.lastrowid
            dash_added = True
            user_added = True
            request_data["dash_id"] = custdashid
            request_data["insert_successful"] = True
        except Exception as e:
            error_dict["Insert Error"] = str(e)
            user_added = False

    else:
        user_added = False

    if user_added == True:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = request_data
        response_dict["links"] = links_dict

        return jsonify(**response_dict)

    else:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
