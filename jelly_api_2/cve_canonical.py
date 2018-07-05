#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/cve/canoncial/{cve_name}/ :
  get:
    description: |
      Gives you all the pops that Jellyfish has recently seen.
    responses:
      200:
        description: OK
    parameters:
      - name: cve_name
        in: path
        description: |
            The CVE you wish to recieve data against
        schema:
          type: string
        required: true
```
"""

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import time
import hashlib
import os
from canonical_cve import shuttlefish

cve_canonical = Blueprint('api2_cve_canonical', __name__)

@cve_canonical.route("/cve/canonical", methods=['GET'])
@cve_canonical.route("/cve/canonical/", methods=['GET'])
@cve_canonical.route("/cve/canonical/<string:cve_name>", methods=['GET'])
@cve_canonical.route("/cve/canonical/<string:cve_name>/", methods=['GET'])
def api2_cve_canonical(cve_name=None):

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Canonical CVE Information for Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()

    argument_error = False

    if "cve_name" in request.args :
        try:
            cve_name = ast.literal_eval(request.args["cve_name"])
        except Exception as e :
            argument_error = True
            error_dict["cve_parse_error"] = "Can not parse cve"

    requesttime=time.time()

    requesttype = "canonical_cve"

    links_info = dict()

    links_info["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/cve/canonical/"
    links_info["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/cve/"
    links_info["children"] = dict()

    request_data = list()

    # Hash Request For Caching
    if argument_error == False :
        try:
            query_tuple = ( cve_name )
            meta_info["query_tuple"] = query_tuple
            query_string = str(query_tuple)
            cache_hash_object = hashlib.sha1(query_string.encode())
            cache_string = cache_hash_object.hexdigest()
        except Exception as e:
            error_dict["cache_hash_error"] = "Error generating cache hash object" + str(e)
            argument_error = True
        else:
            meta_info["cache_hash"] = cache_string

    if argument_error == False :
        meta_info["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + "/cve_" + cache_string + ".json"

    if argument_error == False and os.path.isfile(meta_info["this_cached_file"]) is True  :
        # There's a Cache File see if it's fresh
        cache_file_stats = os.stat(meta_info["this_cached_file"])
        # Should be timestamp of file in seconds
        cache_file_create_time  = int(cache_file_stats.st_ctime)
        if cache_file_create_time > g.MIDNIGHT :
            # Cache is fresh as of midnight
            with open(meta_info["this_cached_file"]) as cached_data :
                try:
                    cached = json.load(cached_data)
                except Exception as e :
                    print("Error reading cache file: " + meta_info["this_cached_file"] + " with error " + str(e) )
                else:
                    return jsonify(**cached)

    do_query = True


    # Select Query
    if do_query and argument_error == False :
        this_cve_data =  shuttlefish(cve=cve_name)
    else :
        error_dict["do_query"] = "Query Ignored"
        this_cve_data = False

    if this_cve_data != False :
        collections_good = True
        # Hydrate the dict with type & ids to be jsonapi compliant
        request_data.append(this_cve_data)
    else :
        error_dict["ERROR"] = ["No Collections"]
        collections_good = False

    if collections_good :

        response_dict = dict()

        response_dict = dict()
        response_dict["meta"] = meta_info
        response_dict["data"] = request_data
        response_dict["links"] = links_info

        # Write Request to Disk.
        try:
            with open(meta_info["this_cached_file"], 'w') as cache_file_object :
                json.dump(response_dict, cache_file_object)
        except Exception as e :
            print("Error writing file " + str(meta_info["this_cached_file"]) + " with error " + str(e))
        else:
            pass
            #print("Cache File wrote to " + str(meta_info["this_cached_file"]) + " at timestamp " + str(g.NOW))

        return jsonify(**response_dict)
    else :
        return jsonify(meta=meta_info, errors=error_dict, links=links_info)

