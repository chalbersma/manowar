#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/collected/values endpoint
Designed to grab information about information as it exists on the edge
(according to our latest collected data). 
* Returns a list of types on the server.

```swagger-yaml
/collected/values/{ctype}:
  x-cached-length: "Every Midnight"
  get:
    description: |
      Grabs information on host collections as it exists on the edge (according
      to our latest collected data). This query can be intensive so it is cached
      daily.
    tags:
      - collections
    responses:
      200:
        description: OK
    parameters:
      - name: ctype
        in: path
        description: |
          The Collection Type you wish to match against. Must be equal to this item.
          You can get a list of collection types from the `/collection/type/` endpoint.
          Can be overrriden by query string parameter.
        schema:
          type: string
        required: true
      {{ hosts | indent(6, True) }}
      {{ exact | indent(6, True) }}
      {{ col | indent(6, True) }}
```
'''

import json
import ast
import time
import os
import hashlib

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory, abort

import manoward


collected_values = Blueprint('api2_collected_values', __name__)


@collected_values.route("/collected/values", methods=['GET'])
@collected_values.route("/collected/values/", methods=['GET'])
@collected_values.route("/collected/values/<string:ctype>", methods=['GET'])
@collected_values.route("/collected/values/<string:ctype>/", methods=['GET'])
def api2_collected_values(ctype="none"):
    '''
    Get's Actual Collections about a Particular Collection Type
    With Lot's of Filters
    '''

    args_def = {"ctype": {"req_type": str,
                          "default": ctype,
                          "required": True,
                          "sql_param": True,
                          "sql_clause": "collection.collection_type = %s",
                          "qdeparse": False}}

    args = manoward.process_args(args_def,
                                 request.args,
                                 coll_lulimit=g.twoDayTimestamp,
                                 include_hosts_sql=True,
                                 include_coll_sql=True,
                                 include_exact=True)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 : Collected values for type {}".format(
        args["ctype"])
    meta_dict["status"] = "In Progress"

    # TODO
    links_dict["children"] = {}

    links_dict["parent"] = "{}{}/collected/subtypes/".format(g.config_items["v2api"]["preroot"],
                                                             g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/collected/values/{}?{}".format(g.config_items["v2api"]["preroot"],
                                                              g.config_items["v2api"]["root"],
                                                              args["ctype"],
                                                              args["qdeparsed_string"])

    requesttype = "collected_value"

    collected_values_query = '''SELECT collection_id, collection_type, collection_subtype, collection_value,
                                    UNIX_TIMESTAMP(collection.initial_update) as initial_update,
                                    UNIX_TIMESTAMP(collection.last_update) as last_update,
                                    {}
                                    FROM collection
                                    JOIN hosts ON fk_host_id = hosts.host_id
                                    where {}'''.format(" , ".join(g.host_data_columns),
                                                       "  and  ".join(args["args_clause"]))

    results = manoward.run_query(g.cur,
                                 collected_values_query,
                                 args=args["args_clause_args"],
                                 one=False,
                                 do_abort=True,
                                 require_results=False)

    for this_coll in results.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_coll["collection_id"]
        this_results["attributes"] = this_coll

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
