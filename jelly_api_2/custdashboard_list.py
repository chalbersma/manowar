#!/usr/bin/env python3

'''
Copyright 2018, VDMS
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
```

'''

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory
import json
import ast
import time
import os
import hashlib

custdashboard_list = Blueprint('api2_custdashboard_list', __name__)


@custdashboard_list.route("/custdashboard/list", methods=['GET'])
@custdashboard_list.route("/custdashboard/list/", methods=['GET'])
@custdashboard_list.route("/custdashboard/list/<int:dash_id>", methods=['GET'])
@custdashboard_list.route("/custdashboard/list/<int:dash_id>/", methods=['GET'])
@custdashboard_list.route("/custdashboard/list/<string:dash_name>", methods=['GET'])
@custdashboard_list.route("/custdashboard/list/<string:dash_name>/", methods=['GET'])
def api2_custdashboard_list(dash_id=None, dash_name=None):

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    where_clauses = list()
    where_clause_args = list()

    if dash_id != None:
        # Use Dash ID
        where_clauses.append(" custdashboardid = %s ")
        where_clause_args.append(int(dash_id))
    elif dash_name != None:
        where_clauses.append(" dashboard_name REGEXP %s ")
        where_clause_args.append(str(dash_name))
    else:
        # List them All!
        pass

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 Customdashboard List Dashboards "
    meta_dict["status"] = "In Progress"
    meta_dict["request_tuple"] = (dash_id, dash_name)

    if argument_error == False:
        hash_string = str(meta_dict["request_tuple"])
        cache_hash_object = hashlib.sha512(hash_string.encode())
        cache_string = cache_hash_object.hexdigest()
        meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + \
            "/custdashboard_list_"+cache_string+".json"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/custdashboard"

    requesttype = "customdashboard_list_item"

    do_query = True

    #print(meta_dict, argument_error)

    # Check to see if a Cache File exists
    # There's no Cacheing on this Endoint!
    '''
    if argument_error == False and os.path.isfile(meta_dict["this_cached_file"]) is True  :
        # There's a Cache File see if it's fresh
        cache_file_stats = os.stat(meta_dict["this_cached_file"])
        # Should be timestamp of file in seconds
        cache_file_create_time  = int(cache_file_stats.st_ctime)
        if cache_file_create_time > g.MIDNIGHT :
            # Cache is fresh as of midnight
            with open(meta_dict["this_cached_file"]) as cached_data :
                try:
                    cached = json.load(cached_data)
                except Exception as e :
                    print("Error reading cache file: " + meta_dict["this_cached_file"] + " with error " + str(e) )
                else:
                    return jsonify(**cached)
    '''

    if len(where_clause_args) > 0:
        where_string = " where "
    else:
        where_string = " "

    where_clause_string = " and ".join(where_clauses)

    list_custdashboard_query = '''select custdashboardid, owner, dashboard_name,
                                dashboard_description from custdashboard'''

    list_custdashboard_query = list_custdashboard_query + \
        where_string + where_clause_string

    print(do_query, argument_error)

    if do_query and argument_error == False:
        # print(audit_result_query)
        g.cur.execute(list_custdashboard_query, where_clause_args)
        all_custdashboards = g.cur.fetchall()
        amount_of_dashboards = len(all_custdashboards)
    else:
        error_dict["do_query"] = "Query Ignored"
        amount_of_dashboards = 0

    if amount_of_dashboards > 0:
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_custdashboards)):
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = all_custdashboards[i]["custdashboardid"]
            this_results["attributes"] = all_custdashboards[i]

            # Now pop this onto request_data
            request_data.append(this_results)
        collections_good = True

    else:
        error_dict["ERROR"] = "No Dashbaords"
        collections_good = False

    if collections_good:

        response_dict = dict()

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = request_data
        response_dict["links"] = links_dict

        # Write Request to Disk.
        '''
        try:
            with open(meta_dict["this_cached_file"], 'w') as cache_file_object :
                json.dump(response_dict, cache_file_object)
        except Exception as e :
            print("Error writing file " + str(meta_dict["this_cached_file"]) + " with error " + str(e))
        else:
            print("Cache File wrote to " + str(meta_dict["this_cached_file"]) + " at timestamp " + str(g.NOW))
        '''

        return jsonify(**response_dict)
    else:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
