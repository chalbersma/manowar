#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/sapi/listusers endpoint. Designed to return info about the hosts

```swagger-yaml
/sapi/listusers/ :
  get:
    description: |
      Designed to grab a list of hosts that either pass or fail an audit
      along with the relevant data about each host. Similar to the audit_table
      item from the old api.
    tags:
      - auth
    responses:
      200:
        description: OK
    parameters:
      - name: apiuid
        in: query
        description: |
          API User Ids
        schema:
          type: integer
        required: false
      - name: apiusername
        in: query
        description: |
          The username associated with the Username. Regex (Unless Exact used)
        schema:
          type: string
        required: false
      - name: apiuser_purpose
        in: query
        description: |
          The API Purpose of the Usernames. Regex (Unless Exact)
        schema:
          type: string
        required: false
```

'''

import json

from flask import Blueprint, g, jsonify

import manoward

sapi_listusers = Blueprint('api2_sapi_listusers', __name__)



@sapi_listusers.route("/listusers", methods=['GET'])
@sapi_listusers.route("/listusers/", methods=['GET'])
@sapi_listusers.route("/sapi/listusers", methods=['GET'])
@sapi_listusers.route("/sapi/listusers/", methods=['GET'])
def api2_sapi_listusers():

    args_def = args_def = {"apiuid": {"req_type": int,
                                        "default": None,
                                        "required": False,
                                        "positive" : True,
                                        "sql_param" : True,
                                        "sql_clause" : " apiuid = %s ",
                                        "qdeparse" : True},
                           "apiusername": {"req_type": str,
                                           "default": None,
                                           "required": False,
                                           "sql_param": True,
                                           "sql_clause": "apiusername REGEXP %s",
                                           "sql_exact_clause": "apiusername = %s",
                                           "qdeparse" : True},
                           "apiuser_purpose": {"req_type": str,
                                               "default": None,
                                               "required": False,
                                               "sql_param": True,
                                               "sql_clause": "apiuser_purpose REGEXP %s",
                                               "sql_exact_clause": "apiuser_purpose = %s",
                                               "qdeparse" : True}
                           }

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_exact=True)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 SAPI List Users "
    meta_dict["status"] = "In Progress"

    links_dict["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/listusers".format(g.config_items["v2api"]["preroot"],
                                                      g.config_items["v2api"]["root"])

    requesttype = "sapi_listusers"

    do_query = True

    if len(args["args_clause"]) > 0:
        where = " where "
    else:
        where = " "

    list_user_query = '''select apiuid, apiusername, apiuser_purpose from apiUsers
                         {} {}'''.format(where,
                                         " and ".join(args["args_clause"]))


    run_result = manoward.run_query(g.cur,
                                    list_user_query,
                                    args=args["args_clause_args"],
                                    do_abort=True)

    for this_user in run_result.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_user["apiuid"]
        this_results["attributes"] = this_user

        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request, links=links_dict)
