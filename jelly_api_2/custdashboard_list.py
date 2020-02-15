#!/usr/bin/env python3

'''
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/custdashboard/list endpoint. Designed to return a list of custom dashboards

```swagger-yaml
/custdashboard/list/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Produces a list of custom dashboards available to query.
    responses:
      200:
        description: OK
    tags:
      - dashboard
    parameters:
      - name: dash_id
        in: query
        description: |
          The Dashbaord identifier you would like to reference. Can be either
          the dashboard short name (does regex search) or the dashboard id number
          (does exact match).
        schema:
          type: integer
        required: false
      - name: dash_name
        in: query
        description: |
          Searches a Regex for the Dashboard Name you're looking for.
        schema:
          type: integer
        required: false
      {{ exact | indent(6, True) }}
```

'''

from flask import Blueprint, g, request, jsonify

import manoward

custdashboard_list = Blueprint('api2_custdashboard_list', __name__)


@custdashboard_list.route("/custdashboard/list", methods=['GET'])
@custdashboard_list.route("/custdashboard/list/", methods=['GET'])
@custdashboard_list.route("/custdashboard/list/<int:dash_id>", methods=['GET'])
@custdashboard_list.route("/custdashboard/list/<int:dash_id>/", methods=['GET'])
@custdashboard_list.route("/custdashboard/list/<string:dash_name>", methods=['GET'])
@custdashboard_list.route("/custdashboard/list/<string:dash_name>/", methods=['GET'])
def api2_custdashboard_list(dash_id=None, dash_name=None):

    '''
    List Avaialable Custom Dashboard
    '''

    args_def = args_def = {"dash_id": {"req_type": int,
                                        "default": None,
                                        "required": False,
                                        "positive" : True,
                                        "sql_param" : True,
                                        "sql_clause" : "custdashboardid = %s",
                                        "qdeparse" : True},
                           "dash_name": {"req_type": str,
                                         "default": None,
                                         "required": False,
                                         "sql_param": True,
                                         "sql_clause": "dashboard_name REGEXP %s",
                                         "sql_exact_clause": "dashboard_name REGEXP %s",
                                         "qdeparse" : True}
                           }

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_exact=True)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    meta_dict["version"] = "2.6"
    meta_dict["name"] = "Jellyfish API Version 2 Customdashboard List Dashboards "
    meta_dict["status"] = "In Progress"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/custdashboard/list?{}".format(g.config_items["v2api"]["preroot"],
                                                             g.config_items["v2api"]["root"],
                                                             args["qdeparsed_string"])

    req_type = "customdashboard_list_item"


    if len(args["args_clause"]) > 0:
        where_string = " where "
    else:
        where_string = " "

    list_custdashboard_query = '''select custdashboardid, owner, dashboard_name,
                                  dashboard_description from custdashboard
                                  {} {}'''.format(where_string,
                                                  " and ".join(args["args_clause"]))

    results = manoward.run_query(g.cur,
                                 list_custdashboard_query,
                                 args=args["args_clause_args"],
                                 one=False,
                                 do_abort=True,
                                 require_results=False)


    for this_dash in results.get("data", list()):
        this_results = dict()
        this_results["type"] = req_type
        this_results["id"] = this_dash["custdashboardid"]
        this_results["attributes"] = this_dash
        this_results["relationsips"] = dict(dashboard="{}{}/dashboard/{}".format(g.config_items["v2api"]["preroot"],
                                                                                 g.config_items["v2api"]["root"],
                                                                                 this_dash["custdashboardid"]))

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
