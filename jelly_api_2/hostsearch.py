#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

API for Host Information
Should return data about the host & return the collections for this particular host.
```swagger-yaml
/hostsearch/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Designed to grab the host(s) that match a particular hostname. Ideally
      to be used by the SAPI endpoint to extend host collections of a particular
      host (by searching for it in Jellyfish, then extending the collections
      with new data).
    responses:
      200:
        description: OK
    tags:
      - hosts
    parameters:
      - name: ctype
        in: query
        description: |
          A regex to match for the collection_type. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the hostname column in the collection table.
        schema:
          type: string
        required: false
      {{ exact | indent(6, True) }}
      {{ col | indent(6, True) }}
      {{ hosts | indent(6, True) }}
```
'''

import json
import ast
import time
import os
import hashlib

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory

import manoward

hostsearch = Blueprint('api2_hostsearch', __name__)


@hostsearch.route("/hostsearch", methods=['GET'])
@hostsearch.route("/hostsearch/", methods=['GET'])
def api2_hostsearch():
    '''
    Execute a Search for Hosts
    '''

    args_def = {"ctype": {"req_type": str,
                          "default": None,
                          "required": False,
                          "sql_param": True,
                          "sql_clause": "collection.collection_type REGEXP %s",
                          "sql_exact_clause": "collection.collection_type = %s",
                          "qdeparse": True}}

    args = manoward.process_args(args_def,
                                 request.args,
                                 lulimit=g.twoDayTimestamp,
                                 include_hosts_sql=True,
                                 include_coll_sql=True,
                                 include_exact=True)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()

    if args.get("ctype", None) is None and args.get("csubtype", None) is None and args.get("value", None) is None:
        col_join = str()
    else:
        g.logger.debug(
            "I need Collections Joined. This may Slow down my Query.")
        col_join = "join collection on host_id = collection.fk_host_id"

        args["args_clause"].append(
            "collection.last_update >= FROM_UNIXTIME(%s)")
        args["args_clause_args"].append(g.twoDayTimestamp)

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 Host Search results."
    meta_dict["status"] = "In Progress"

    links_dict["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/hostsearch?{}".format(g.config_items["v2api"]["preroot"],
                                                     g.config_items["v2api"]["root"],
                                                     args["qdeparsed_string"])

    requesttype = "hostquery"

    host_search = '''SELECT {0}
                     FROM hosts
                     {1}
                     WHERE {2}
                     GROUP by host_id'''.format(" , ".join(g.host_data_columns),
                                                col_join,
                                                " and ".join(args["args_clause"]))

    results = manoward.run_query(g.cur,
                                 host_search,
                                 args=args["args_clause_args"],
                                 one=False,
                                 do_abort=True,
                                 require_results=False)

    for this_host in results.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_host["host_id"]
        this_results["attributes"] = this_host
        this_results["relationships"] = dict()
        this_results["relationships"]["host_collections"] = "{}{}/hostcollections/{}".format(g.config_items["v2api"]["preroot"],
                                                                                             g.config_items["v2api"]["root"],
                                                                                             this_host["host_id"])

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
