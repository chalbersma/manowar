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

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory
import json
import ast
import time
import os



collected_subtypes = Blueprint('api2_collected_subtype', __name__)

@collected_subtypes.route("/collected/subtypes", methods=['GET'])
@collected_subtypes.route("/collected/subtypes/", methods=['GET'])
@collected_subtypes.route("/collected/subtypes/<string:ctype>", methods=['GET'])
@collected_subtypes.route("/collected/subtypes/<string:ctype>/", methods=['GET'])
def api2_collected_types(ctype="none"): 

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    if "ctype" in request.args :
        ctype = request.args["ctype"]

    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish API Version 2 : Collected Subtypes for type " + ctype
    meta_dict["status"] = "In Progress"
    meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + "/collected_subtypes_" + ctype + ".json"
    meta_dict["NOW"] = g.NOW

    links_dict["children"] = { "types" : ( g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/values" ) }
    links_dict["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/types"
    links_dict["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/subtypes"

    requesttype = "collection_subtype"

    do_query = True

    # Check to see if a Cache File exists
    if os.path.isfile(meta_dict["this_cached_file"]) is True :
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

    # Means that the cache file doesn't exit or isn't fresh

    # Have a deterministic query so that query caching can do it's job
    collected_subtypes_filtered_query_args = [ str(g.twoDayTimestamp), str(ctype)]
    collected_subtype_query="select distinct(collection_subtype) from collection where last_update >= FROM_UNIXTIME( %s ) and collection_type = %s ; "

    if do_query :
        g.cur.execute(collected_subtype_query, collected_subtypes_filtered_query_args)
        all_subtypes = g.cur.fetchall()
        amount_of_subtypes = len(all_subtypes)
    else :
        error_dict["do_query"] = "Query Ignored"
        amount_of_types = 0

    if amount_of_subtypes > 0 :
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_subtypes)) :
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = i
            this_results["attributes"] = all_subtypes[i]

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
            with open(meta_dict["this_cached_file"], 'w') as cache_file_object :
                json.dump(response_dict, cache_file_object)
        except Exception as e :
            print("Error writing file " + str(meta_dict["this_cached_file"]) + " with error " + str(e))
        else:
            print("Cache File wrote to " + str(meta_dict["this_cached_file"]) + " at timestamp " + str(g.NOW))


        return jsonify(**response_dict)
    else :

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)

    
