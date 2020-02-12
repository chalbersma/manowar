#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/custdashboard/list/{dash_id} endpoint. Designed to return a list of custom dashboards

```swagger-yaml
/custdashboard/dashboard/{dash_id}/ :
  x-cached-length: "Never"
  get:
    description: |
      Produces a the Audits inside of a custom dashboard.
    responses:
      200:
        description: OK
    tags:
      - dashboard
    parameters:
      - name: dash_id
        in: path
        description: |
            The Dashbaord identifier you would like to reference. Can be either
            the dashboard short name or the dashboard id number
        schema:
          type: string
        required: true
```

'''

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory
import json
import ast
import time
import os
import hashlib

custdashboard_dashboard = Blueprint('api2_custdashboard_dashboard', __name__)


@custdashboard_dashboard.route("/custdashboard/dashboard/<int:dash_id>", methods=['GET'])
@custdashboard_dashboard.route("/custdashboard/dashboard/<int:dash_id>/", methods=['GET'])
@custdashboard_dashboard.route("/custdashboard/dashboard/<string:dash_name>", methods=['GET'])
@custdashboard_dashboard.route("/custdashboard/dashboard/<string:dash_name>/", methods=['GET'])
def api2_custdashboard_dashboard(dash_id=None, dash_name=None):

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    where_clauses = list()
    where_clause_args = list()

    if dash_id == None and dash_name == None:
        # Recieved Nothing (Acutally shouldn't route here in theory)
        argument_error = True
    else:
        if dash_id != None:
            # Use Dash ID
            where_clauses.append(" custdashboard.custdashboardid = %s ")
            where_clause_args.append(int(dash_id))
        elif dash_id != None:
            where_clauses.append(" custdashboard.dashboard_name = %s ")
            where_clause_args.append(str(dashboard_name))
        else:
            argument_error = True

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 Customdashboard List Single Dashboard"
    meta_dict["status"] = "In Progress"

    if argument_error == False:
        hash_string = str(where_clause_args)
        cache_hash_object = hashlib.sha512(hash_string.encode())
        cache_string = cache_hash_object.hexdigest()
        meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + \
            "/custdash_" + cache_string + ".json"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/custdashboard/list"

    requesttype = "customdashboard_list_dashboard"

    do_query = True

    #print(meta_dict, argument_error)

    # Check to see if a Cache File exists
    if argument_error == False and os.path.isfile(meta_dict["this_cached_file"]) is True:
        # There's a Cache File see if it's fresh
        cache_file_stats = os.stat(meta_dict["this_cached_file"])
        # Should be timestamp of file in seconds
        cache_file_create_time = int(cache_file_stats.st_ctime)
        if cache_file_create_time > g.MIDNIGHT:
            # Cache is fresh as of midnight
            with open(meta_dict["this_cached_file"]) as cached_data:
                try:
                    cached = json.load(cached_data)
                except Exception as e:
                    print("Error reading cache file: " +
                          meta_dict["this_cached_file"] + " with error " + str(e))
                else:
                    return jsonify(**cached)

    where_clause_string = " and ".join(where_clauses)
    if len(where_clause_args) > 0:
        where_bits = " where "
    else:
        where_bits = " "

    list_custdashboard_query = '''select
                                    membershipid, fk_custdashboardid, fk_audits_id,
                                    dashboard_name, audit_name, audit_short_description,
                                    audit_primary_link, audit_priority
                                from custdashboardmembers
                                JOIN custdashboard
                                on fk_custdashboardid = custdashboardid
                                JOIN audits
                                on fk_audits_id = audit_id
                                '''
    list_custdashboard_query = list_custdashboard_query + \
        where_bits + where_clause_string

    print("we here")

    if do_query and argument_error == False:
        # print(audit_result_query)
        g.cur.execute(list_custdashboard_query, where_clause_args)
        custdashboard = g.cur.fetchall()
        custdashboard_results = len(custdashboard)
    else:
        error_dict["do_query"] = "Query Ignored"
        custdashboard_results = 0

    if custdashboard_results > 0:
        # Hydrate the dict with type & ids to be jsonapi compliant
        for result in custdashboard:
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = result["membershipid"]
            this_results["attributes"] = result

            # Now pop this onto request_data
            request_data.append(this_results)
        collections_good = True

    else:
        error_dict["ERROR"] = "No Audits"
        collections_good = False

    if collections_good:

        response_dict = dict()

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = request_data
        response_dict["links"] = links_dict

        print(response_dict)

        # Write Request to Disk.
        try:
            with open(meta_dict["this_cached_file"], 'w') as cache_file_object:
                json.dump(response_dict, cache_file_object)
        except Exception as e:
            print("Error writing file " +
                  str(meta_dict["this_cached_file"]) + " with error " + str(e))
        else:
            print("Cache File wrote to " +
                  str(meta_dict["this_cached_file"]) + " at timestamp " + str(g.NOW))

        return jsonify(**response_dict)
    else:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
