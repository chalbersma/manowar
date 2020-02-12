#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/factorlist/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Gives you all the pops that Jellyfish has recently seen.
    tags:
      - audits
    responses:
      200:
        description: OK
    parameters:
      - name: factor
        in: query
        description: |
          The Factor to discriminate on. Must be a known & collated type
        schema:
          type: string
          enum:
            - pop
            - srvtype
      {{ hosts | indent(6, True) }}
      {{ exact | indent(6, True) }}
```
"""

import json
import ast
import time
import hashlib
import os

from flask import current_app, Blueprint, g, request, jsonify, abort

import manoward


factorlist = Blueprint('api2_factorlist', __name__)


@factorlist.route("/factorlist", methods=['GET'])
@factorlist.route("/factorlist/", methods=['GET'])
@factorlist.route("/poplist", methods=['GET'])
@factorlist.route("/poplist/", methods=['GET'])
@factorlist.route("/srvtypelist", methods=['GET'])
@factorlist.route("/srvtypelist/", methods=['GET'])
def api2_factorlist(factor="pop"):
    '''
    List Pops,
    Optionally List pops that have hosts contained within
    '''

    if request.url_rule.rule.startswith("pop"):
        factor = "pop"
    elif request.url_rule.rule.startswith("srv"):
        factor = "srvtype"

    args_def = {"factor": {"req_type": str,
                           "default": factor,
                           "required": True,
                           "sql_param": False,
                           "qdeparse": True,
                           "enum": ("pop", "srvtype")}  # Extend when the time comes
                }

    args = manoward.process_args(args_def,
                                 request.args,
                                 lulimit=g.twoDayTimestamp,
                                 include_hosts_sql=True,
                                 include_exact=True)

    request_data = list()
    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Factor ({}) List for Jellyfish2 API Version 2 ".format(
        args["factor"])
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()

    requesttype = "factor_list"

    links_info = dict()

    links_info["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_info["self"] = "{}{}/factorlist?{}".format(g.config_items["v2api"]["preroot"],
                                                     g.config_items["v2api"]["root"],
                                                     args["qdeparsed_string"])

    factor_list_query = '''select DISTINCT {} as factor
                            from hosts
                            where {}'''.format(args["factor"],
                                               "  and  ".join(args["args_clause"]))

    results = manoward.run_query(g.cur,
                                 factor_list_query,
                                 args=args["args_clause_args"],
                                 one=False,
                                 do_abort=True,
                                 require_results=False)

    for this_factor in results.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_factor["factor"]
        this_results["attributes"] = this_factor
        this_results["relationships"] = dict()
        this_results["relationships"]["hostsof"] = "{}{}/hostsearch/?{}={}&{}".format(g.config_items["v2api"]["preroot"],
                                                                                      g.config_items["v2api"]["root"],
                                                                                      args["factor"],
                                                                                      this_factor["factor"],
                                                                                      args["qdeparsed_string"])

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_info, data=request_data, links=links_info)
