#!/usr/bin/env python3

'''
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/custdashboard/create  endpoint. Designed to initiate a sapi API user.

```swagger-yaml
/custdashboard/create/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Creates a New Custom Dashboard
    responses:
      200:
        description: OK
    tags:
      - dashboard
    parameters:
      - name: dashboard_name
        in: query
        description: |
          Username that wants to be created.
        schema:
          type: string
        required: true
      - name: dashboard_description
        in: query
        description: |
          Accompying Description to go with this Dashboard
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
def api2_custdashboard_create():

    """
    Crete a New API User
    """


    args_def = args_def = {"dashboard_name": {"req_type": str,
                                        "default": None,
                                        "required": True,
                                        "require_alpha" : True,
                                        "require_lower" : True,
                                        "qdeparse" : True},
                           "dashboard_description": {"req_type": str,
                                                     "default": None,
                                                     "required": True,
                                                     "qdeparse" : True}
                           }

    args = manoward.process_args(args_def,
                                 request.args)

    meta_dict = dict()
    request_data = dict()
    links_dict = dict()
    error_dict = dict()

    this_endpoint_restrictions = (
        ("conntype", "whitelist"), ("conntype", "robot"))
    this_endpoint_endorsements = (("conntype", "ldap"), )

    manoward.process_endorsements(endorsements=this_endpoint_endorsements,
                                  restrictions=this_endpoint_restrictions,
                                  session_endorsements=g.session_endorsements,
                                  session_restrictions=g.session_restrictions,
                                  ignore_abort=g.debug)

    meta_dict["version"] = "2.6"
    meta_dict["name"] = "Manowar API Version 2 Custdashboard Create "
    meta_dict["status"] = "In Progress"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_info["self"] = "{}{}/custdashboard/create?{}".format(g.config_items["v2api"]["preroot"],
                                                               g.config_items["v2api"]["root"],
                                                               args.get("qdeparsed_string", ""))

    requesttype = "custdashboard_create"

    insert_args = [g.USERNAME, args["dashboard_name"], args["dashboard_description"]]
    insert_query = ''' insert into custdashboard ( owner, dashboard_name,
                       dashboard_description ) VALUES ( %s , %s , %s )
                       '''

    try:
        g.cur.execute(insert_query, insert_args)
        custdashid = g.cur.lastrowid
        dash_added = True
    except Exception as e:
        error_dict["Insert Error"] = str(e)
        error_dict["Unable to Insert, is this Dashboard already Known?"]
        dash_added = False
    else:
        request_data["dash_id"] = custdashid
        request_data["insert_successful"] = dash_added
        request_data["relationships"]["dashboard"] = "{}{}/dashboard/{}".format(g.config_items["v2api"]["preroot"],
                                                                                g.config_items["v2api"]["root"],
                                                                                custdashid)

    if dash_added:
        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = request_data
        response_dict["links"] = links_dict
    else:
        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

    return jsonify(**response_dict)
