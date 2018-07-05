#!/usr/bin/env python3


'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/collected/types endpoint
Designed to grab information about information as it exists on the edge
(according to our latest collected data). 
* Returns a list of types on the server.

```swagger-yaml
/collected/types/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Grabs a list of types available in our collections. This is a slower query, so
      results are cached once at midnight. If you query times out it will finish up
      the query & caching on the server and then serve it to you next time you ask.
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


collected_types = Blueprint('api2_collected_type', __name__)

@collected_types.route("/collected/types", methods=['GET'])
@collected_types.route("/collected/types/", methods=['GET'])
def api2_collected_types(): 

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish API Version 2 : Collected Types"
    meta_dict["status"] = "In Progress"
    meta_dict["cached_file"] = g.config_items["v2api"]["cachelocation"] + "/collected_types_cache.json"
    meta_dict["NOW"] = g.NOW

    links_dict["children"] = { "types" : ( g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/types/subtypes" ) }
    links_dict["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected"
    links_dict["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/types"

    requesttype = "collection_type"

    do_query = True

    # Check to see if a Cache File exists
    if os.path.isfile(meta_dict["cached_file"]) is True :
        # There's a Cache File see if it's fresh
        cache_file_stats = os.stat(meta_dict["cached_file"])
        # Should be timestamp of file in seconds
        cache_file_create_time  = int(cache_file_stats.st_ctime)
        if cache_file_create_time > g.MIDNIGHT :
            # Cache is fresh as of midnight
            with open(meta_dict["cached_file"]) as cached_data :
                try:
                    cached = json.load(cached_data)
                except Exception as e :
                    print("Error reading cache file: " + meta_dict["cached_file"] + " with error " + str(e) )
                else:
                    return jsonify(**cached)

    # Means that the cache file doesn't exit or isn't fresh

    # Have a deterministic query so that query caching can do it's job
    collected_type_args=[ str(g.twoDayTimestamp) ]
    collected_type_query="select distinct(collection_type) from collection where last_update >= FROM_UNIXTIME( %s ) ; "

    if do_query :
        g.cur.execute(collected_type_query, collected_type_args)
        all_types = g.cur.fetchall()
        amount_of_types = len(all_types)
    else :
        error_dict["do_query"] = "Query Ignored"
        amount_of_types = 0

    if amount_of_types > 0 :
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_types)) :
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = i
            this_results["attributes"] = all_types[i]

            # Now pop this onto request_data
            request_data.append(this_results)

        # Move onto the next one
        collections_good = True

    else :
        error_dict["ERROR"] = ["No Collections"]
        collections_good = False



    if collections_good :

        response_dict = dict()

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = request_data
        response_dict["links"] = links_dict

        # Write Request to Disk.
        try:
            with open(meta_dict["cached_file"], 'w') as cache_file_object :
                json.dump(response_dict, cache_file_object)
        except Exception as e :
            print("Error writing file " + str(meta_dict["cached_file"]) + " with error " + str(e))
        else:
            print("Cache File wrote to " + str(meta_dict["cached_file"]) + " at timestamp " + str(g.NOW))


        return jsonify(**response_dict)
    else :

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)

    
