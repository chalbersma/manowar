#!/usr/bin/env python3


'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/collected/subtypes endpoint
Designed to grab information about information as it exists on the edge
(according to our latest collected data). 
* Returns a list of types on the server.

```swagger-yaml
/collected/subtypes/{ctype}/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
     Grabs a list of subtypes associated with a particular type. As this query can be intesive,
     results are cached once a midnight. Please be patient with this query.
    responses:
     200:
       description: OK
    tags:
     - collections
    parameters:
     - name: ctype
       in: path
       description: | 
         The Collection Type you wish to match against. Must be equal to this item. You can get
         a list of collection types from the `/collection/type` endpoint. Can be overridden with
         query string paramter.
       required: true
       schema:
         type: string
```
'''

import json
import ast
import time
import os

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory

import manoward


collected_subtypes = Blueprint('api2_collected_subtype', __name__)


@collected_subtypes.route("/collected/subtypes", methods=['GET'])
@collected_subtypes.route("/collected/subtypes/", methods=['GET'])
@collected_subtypes.route("/collected/subtypes/<string:ctype>", methods=['GET'])
@collected_subtypes.route("/collected/subtypes/<string:ctype>/", methods=['GET'])
def api2_collected_types(ctype="none"):
    '''
    Return the Available Subtypes for a particular type
    '''

    args_def = {"ctype": {"req_type": str,
                          "default": ctype,
                          "required": True,
                          "sql_param": True,
                          "sql_clause": "collection_type = %s",
                          "qdeparse": False}
                }

    args = manoward.process_args(
        args_def, request.args, lulimit=g.twoDayTimestamp)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 : Collected Subtypes for type {}".format(
        args["ctype"])
    meta_dict["status"] = "In Progress"

    links_dict["children"] = dict()
    links_dict["parent"] = "{}{}/collected/types".format(g.config_items["v2api"]["preroot"],
                                                         g.config_items["v2api"]["root"])
    links_dict["self"] = "{}{}/collected/subtypes/{}".format(g.config_items["v2api"]["preroot"],
                                                             g.config_items["v2api"]["root"],
                                                             args["ctype"])

    requesttype = "collection_subtype"

    # Have a deterministic query so that query caching can do it's job
    collected_subtypes_filtered_query_args = [
        str(g.twoDayTimestamp), str(ctype)]
    collected_subtype_query = '''select distinct(collection_subtype) as subtype_name from collection
                                    where {}'''.format(" and ".join(args["args_clause"]))

    results = manoward.run_query(g.cur,
                                 collected_subtype_query,
                                 args=args["args_clause_args"],
                                 one=False,
                                 do_abort=True,
                                 require_results=False)

    for this_subtype in results.get("data", list()):

        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_subtype["subtype_name"]
        this_results["attributes"] = this_subtype
        this_results["relationships"] = {"values": "{}{}/collected/values/{}/{}".format(g.config_items["v2api"]["preroot"],
                                                                                        g.config_items["v2api"]["root"],
                                                                                        args["ctype"],
                                                                                        this_subtype["subtype_name"])}

        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
