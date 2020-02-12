#!/usr/bin/env python3


'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/collected/subtypes endpoint
Designed to grab information about information as it exists on the edge
(according to our latest collected data). 
* Returns a list of types on the server.

```swagger-yaml
/collected/subtypes_filtered/{ctype}/ :
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
      - name: usevalue
        schema:
          type: string
          enum: [true, false]
        in: query
        description: |
          Setting this value to anything will tell the api endpoint to not just organize subtypes but
          to also organize unique values too.
      {{ hosts | indent(6, True) }}
      {{ exact | indent(6, True) }}
```
'''

import json
import ast
import time
import os
import hashlib

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory

import manoward

collected_subtypes_filtered = Blueprint(
    'api2_collected_subtype_filtered', __name__)


@collected_subtypes_filtered.route("/collected/subtypes_filtered", methods=['GET'])
@collected_subtypes_filtered.route("/collected/subtypes_filtered/", methods=['GET'])
@collected_subtypes_filtered.route("/collected/subtypes_filtered/<string:ctype>", methods=['GET'])
@collected_subtypes_filtered.route("/collected/subtypes_filtered/<string:ctype>/", methods=['GET'])
def api2_collected_types_filtered(ctype="none"):
    '''
    A slower filtered subtype query
    '''

    args_def = {"ctype": {"req_type": str,
                          "default": ctype,
                          "required": True,
                          "sql_param": True,
                          "sql_clause": "collection.collection_type = %s",
                          "qdeparse": False},
                "usevalue": {"req_type": str,
                             "default": "false",
                             "required": False,
                             "sql_param": False,
                             "enum": ("true", "false"),
                             "qdeparse": True}
                }

    args = manoward.process_args(args_def, request.args,
                                 coll_lulimit=g.twoDayTimestamp, include_hosts_sql=True,
                                 include_coll_sql=True, include_exact=True)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 : Filtered Collected Subtypes for type {}".format(
        args["ctype"])
    meta_dict["status"] = "In Progress"

    links_dict["parent"] = "{}{}/collected/types".format(g.config_items["v2api"]["preroot"],
                                                         g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/collected/subtypes_filered/{}?{}".format(g.config_items["v2api"]["preroot"],
                                                                        g.config_items["v2api"]["root"],
                                                                        args["ctype"],
                                                                        args["qdeparsed_string"])

    requesttype = "collection_subtype_filtered"

    do_query = True

    if args.get("usevalue", "false") == "true":
        group_value_get = ", collection_value as value "
        group_by_string = " group by collection_subtype, collection_value "
    else:
        group_value_get = " "
        group_by_string = " group by collection_subtype "

    collected_subtype_query = '''select distinct(collection_subtype) as subtype, count(*) as count {0}
                                from collection
                                join hosts ON fk_host_id = hosts.host_id
                                where {1}
                                {2}'''.format(group_value_get,
                                              " and ".join(
                                                  args["args_clause"]),
                                              group_by_string)

    results = manoward.run_query(g.cur,
                                 collected_subtype_query,
                                 args=args["args_clause_args"],
                                 one=False,
                                 do_abort=True,
                                 require_results=False)

    for i in range(0, len(results.get("data", list()))):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = i
        this_results["attributes"] = results.get("data", list())[i]

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
