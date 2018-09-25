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

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory
import json
import ast
import time
import os
import hashlib

hostcollections = Blueprint('api2_hostcollections', __name__)

@hostcollections.route("/hostcollections/", methods=['GET'])
@hostcollections.route("/hostcollections/<int:host_id>", methods=['GET'])
@hostcollections.route("/hostcollections/<int:host_id>/", methods=['GET'])
def api2_hostcollections(host_id=0, collection_subtype=False, collection_value=False):

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    where_clauses = list()
    where_clause_args = list()

    # Grab Values
    if "host_id" in request.args :
        try:
            host_id = ast.literal_eval(request.args["host_id"])
        except Exception as e :
            print("Exception")
            error_dict["host_id read error"] = "Error parsing host_id " + str(e)
            argument_error=True
    if argument_error == False :
        if type(host_id) is int and host_id > 0 :
            hostid_where_clause = " host_id = %s  "
        else :
            error_dict["host_id_type_error"] = "Host_ID isn't a positive integer : " + str(host_id) + ". Shame on you."
            argument_error=True

    if "collection_subtype" in request.args :
        try:
            collection_subtype = ast.literal_eval(request.args["collection_subtype"])
        except Exception as e :
            error_dict["collection_subtype_read_error"] = "Error parsing collection_subtype " + str(e)
            argument_error=True
        else:
            this_clause = " collection_subtype REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_args.append(str(collection_subtype))

    if "collection_type" in request.args :
        try:
            collection_type = ast.literal_eval(request.args["collection_type"])
        except Exception as e :
            error_dict["collection_type_read_error"] = "Error parsing collection_type " + str(e)
            argument_error=True
        else:
            this_clause = " collection_type REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_args.append(str(collection_type))

    # Hash Request For Caching
    if argument_error == False :
        try:
            where_clause_string = " and ".join(where_clauses)
            hash_string=str(where_clause_args)+str(host_id)
            cache_hash_object = hashlib.sha1(hash_string.encode()) # nosec
            cache_string = cache_hash_object.hexdigest()
        except Exception as e:
            error_dict["cache_hash_error"] = "Error generating cache hash object" + str(e)
            argument_error = True
        else:
            meta_dict["cache_hash"] = cache_string

    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish API Version 2 Host Results for Host ID " + str(host_id)
    meta_dict["status"] = "In Progress"

    if argument_error == False :
        meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + "/hostinfo_" + str(host_id) + "#" + cache_string + ".json"


    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/"
    links_dict["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/hostinfo"

    requesttype = "hostinfo"

    do_query = True

    #print(meta_dict, argument_error)

    # Check to see if a Cache File exists
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

        # Have a deterministic query so that query caching can do it's job
    if argument_error == False :

        if len(where_clause_string) > 0 :
            where_joiner = " and "
        else :
            where_joiner = " "
        host_name_query_args = [ str(host_id) ]
        host_name_query = "select host_id, host_uber_id, hostname, pop, srvtype, hoststatus, UNIX_TIMESTAMP(last_update) as last_update from hosts where host_id = %s ; "
        host_collections_query_args = [ str(host_id), str(g.twoDayTimestamp) ]
        host_collections_query_args.extend(where_clause_args)
        # Query is properly paramertized and is split into multiple lines only for
        # the sake of readability.Being split to work around a bandit ast parser bug.
        host_collections_query="select"
        host_collections_query=host_collections_query + " collection_id, collection_subtype, collection_type, collection_value, fk_host_id, " +\
                                    " UNIX_TIMESTAMP(initial_update) as initial_update, UNIX_TIMESTAMP(last_update) as last_update " +\
                                    " from collection where fk_host_id = %s " +\
                                    " and last_update >= FROM_UNIXTIME( %s ) " +\
                                    where_joiner + where_clause_string +\
                                    " group by collection_type, collection_subtype; "


    if do_query and argument_error == False :
        #print("QUERY: ", host_collections_query)
        #print("QUERY: ", host_name_query)
        g.cur.execute(host_name_query, host_name_query_args)
        host_info = g.cur.fetchone()

        g.cur.execute(host_collections_query, host_collections_query_args)
        all_collections = g.cur.fetchall()
        amount_of_hosts = len(all_collections)
    else :
        error_dict["do_query"] = "Query Ignored"
        amount_of_hosts = 0

    if amount_of_hosts > 0 :
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_collections)) :
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = all_collections[i]["collection_id"]
            this_results["attributes"] = all_collections[i]
            this_results["relationships"] = dict()

            # Now pop this onto request_data
            request_data.append(this_results)

        # Move onto the next one
        meta_dict["host_information"] = host_info
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
