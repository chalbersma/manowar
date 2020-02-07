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
    parameters:
      - name: hostname
        in: query
        description: |
          The regex the hostname you wish to get data for.
        schema:
          type: string
        required: false
      - name: exact
        in: query
        description: |
          Boolean use exact matches instead of regex
        schema:
          type: string
        required: false
      - name: pop
        in: query
        description: |
          Pop you wish to search for, respects exact
        schema:
          type: string
        required: false
      - name: srvtype
        in: query
        description: |
          Srvtype you wish to search for, respects exact
        schema:
          type: string
        required: false
      - name: hoststatus
        in: query
        description: |
          Hoststatus you wish to search for, respects exact
        schema:
          type: string
        required: false
      - name: status
        in: query
        description: |
          Overrides hoststatus.
        schema:
          type: string
        required: false
      - name: matchcollection
        in: query
        description: |
          Allow the match of one item joined from the collection table. Default
          is off but if it's on you'll need to provide a collection match object.
        required: false
        schema:
          type: string
      - name: ctype
        in: query
        description: |
          If using matchcollection this is the collection type to match against.
          This is always an exact match.
        required: false
        schema:
          type: string
      - name: csubtype
        in: query
        description: |
          If using matchcollection this is the collection subtype to match against.
          This is always an exact match.
        required: false
        schema:
          type: string
      - name: cvalue
        in: query
        description: |
          If using matchcollection this is the collection value to match against.
          This is always an exact match.
        required: false
        schema:
          type: string
```
'''

import json
import ast
import time
import os
import hashlib

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory

import db_helper

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
                          "sql_exact_clause" : "collection.collection_type = %s",
                          "qdeparse": True}}

    args = db_helper.process_args(args_def,
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
        g.logger.debug("I need Collections Joined. This may Slow down my Query.")
        col_join = "join collection on host_id = collection.fk_host_id"

        args["args_clause"].append("collection.last_update >= FROM_UNIXTIME(%s)")
        args["args_clause_args"].append(g.twoDayTimestamp)


    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish API Version 2 Host Search results."
    meta_dict["status"] = "In Progress"

    links_dict["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/hostsearch?{}".format(g.config_items["v2api"]["preroot"],
                                                     g.config_items["v2api"]["root"],
                                                     args["qdeparsed_string"])


    requesttype = "hostquery"


    host_search = '''SELECT host_id, host_uber_id, hostname, pop, srvtype,
                     hoststatus, UNIX_TIMESTAMP(hosts.last_update) as last_update
                     FROM hosts
                     {0}
                     WHERE {1}
                     GROUP by host_id'''.format(col_join,
                                         " and ".join(args["args_clause"]))


    results = db_helper.run_query(g.cur,
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
