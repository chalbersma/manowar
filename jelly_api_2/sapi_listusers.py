#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/sapi/listusers endpoint. Designed to return info about the hosts

```swagger-yaml
/sapi/listusers/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Designed to grab a list of hosts that either pass or fail an audit
      along with the relevant data about each host. Similar to the audit_table
      item from the old api.
    tags:
      - auth
    responses:
      200:
        description: OK
```

'''

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory
import json
import ast
import time
import os
import hashlib

sapi_listusers = Blueprint('api2_sapi_listusers', __name__)


@sapi_listusers.route("/sapi/listusers", methods=['GET'])
@sapi_listusers.route("/sapi/listusers/", methods=['GET'])
def api2_sapi_listusers():

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    where_clauses = list()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 SAPI List Users "
    meta_dict["status"] = "In Progress"

    if argument_error == False:
        meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + \
            "/sapi_listusers.json"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/sapi"

    requesttype = "sapi_listusers"

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

    list_user_query = "select apiuid, apiusername, apiuser_purpose from apiUsers;"

    if do_query and argument_error == False:
        # print(audit_result_query)
        g.cur.execute(list_user_query)
        all_users = g.cur.fetchall()
        amount_of_users = len(all_users)
    else:
        error_dict["do_query"] = "Query Ignored"
        amount_of_users = 0

    if amount_of_users > 0:
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_users)):
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = all_users[i]["apiuid"]
            this_results["attributes"] = all_users[i]

            # Now pop this onto request_data
            request_data.append(this_results)
        collections_good = True

    else:
        error_dict["ERROR"] = "No Users"
        collections_good = False

    if collections_good:

        response_dict = dict()

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = request_data
        response_dict["links"] = links_dict

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
