#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

API for Host Information
Should return data about the host & return the collections for this particular host.
```swagger-yaml
/hostcollections/{host_id}/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Designed to grab the latest collections from the host. Grabs the fresh
      ones as of yesterday Midnight. Only grabs one collection for each type/subtype
    responses:
      200:
        description: OK
    parameters:
      - name: host_id
        in: path
        description: |
          The id of the host you wish to get data for.
        schema:
          type: integer
        required: true
      - name: collection_type
        x-astliteraleval: true
        in: query
        description: |
          A regex to match for the collection_type. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the hostname column in the collection table.
        schema:
          type: string
        required: false
      - name: collection_subtype
        x-astliteraleval: true
        in: query
        description: |
          A regex to match for the collection_subtype name. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the collection_subtype column in the collection table.
        schema:
          type: string
        required: false
```
'''

import json
import ast
import time
import os
import hashlib

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory, abort

import db_helper

hostcollections = Blueprint('api2_hostcollections', __name__)

@hostcollections.route("/hostcollections/", methods=['GET'])
@hostcollections.route("/hostcollections/<int:host_id>", methods=['GET'])
@hostcollections.route("/hostcollections/<int:host_id>/", methods=['GET'])
def api2_hostcollections(host_id=0):

    args_def = {"hostid": {"req_type": int,
                           "default": host_id,
                           "required": True,
                           "positive": True,
                           "sql_param": True,
                           "sql_clause": " fk_host_id = %s "},
               "ctype": {"req_type": str,
                          "default": None,
                          "required": False,
                          "sql_param": True,
                          "sql_clause": "collection.collection_type REGEXP %s",
                          "sql_exact_clause" : "collection.collection_type = %s",
                          "qdeparse": True}
               }

    args = db_helper.process_args(args_def,
                                  request.args,
                                  coll_lulimit=g.twoDayTimestamp,
                                  include_coll_sql=True,
                                  include_exact=True)


    meta_dict = dict()
    request_data = list()
    links_dict = dict()


    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish API Version 2 Host Results for Host ID {}".format(args["hostid"])
    meta_dict["status"] = "In Progress"

    links_dict["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/hostinfo/{}?{}".format(g.config_items["v2api"]["preroot"],
                                                      g.config_items["v2api"]["root"],
                                                      args["hostid"],
                                                      args["qdeparsed_string"])

    requesttype = "host_collections"


    host_collections_query = '''select collection_id, fk_host_id,
                                UNIX_TIMESTAMP(initial_update) as initial_update,
                                UNIX_TIMESTAMP(collection.last_update) as last_update,
                                hostname, pop, srvtype, hoststatus,
                                collection_type, collection_subtype, collection_value
                                from collection
                                join hosts on collection.fk_host_id = hosts.host_id
                                where {}
                                group by collection_type, collection_subtype'''.format("  and  ".join(args["args_clause"]))

    results = db_helper.run_query(g.cur,
                                  host_collections_query,
                                  args=args["args_clause_args"],
                                  one=False,
                                  do_abort=True,
                                  require_results=False)

    for this_coll in results.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_coll["collection_id"]
        this_results["attributes"] = this_coll
        this_results["relationships"] = dict()

        # Now pop this onto request_data
        request_data.append(this_results)


    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
