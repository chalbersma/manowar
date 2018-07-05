#!/usr/bin/env python3


'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/collected/subtypes endpoint
Designed to grab information about information as it exists on the edge
(according to our latest collected data). 
* Returns a list of types on the server.

```swagger-yaml
/collected/subtypes_filtered/{ctype}/ :
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
      x-astliteraleval: true
    - name: csubtype
      in: query
      description: |
        The Collection Subtype you wish to match against. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
        regular expressions are accepted. Matched on the collection_subtype column in the collection table.
      schema:
        type: string
      required: false
    - name: usevalue
      schema:
        type: string
      in: query
      description: |
        Setting this value to anything will tell the api endpoint to not just organize subtypes but
        to also organize unique values too.
    - name: hostname
      x-astliteraleval: true
      in: query
      description: |
        A regex to match for the hostname. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
        regular expressions are accepted. Matched on the hostname column in the host table.
      schema:
        type: string
      required: false
    - name: pop
      x-astliteraleval: true
      in: query
      description: |
        A regex to match for the pop name. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
        regular expressions are accepted. Matched on the pop column in the host table.
      schema:
        type: string
      required: false
    - name: srvtype
      x-astliteraleval: true
      in: query
      description: |
        A regex to match for the srvtype name. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
        regular expressions are accepted. Matched on the srvtype column in the host table.
      schema:
        type: string
      required: false
    - name: value
      x-astliteraleval: true
      in: query
      description: |
        A regex to match for the value. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
        regular expressions are accepted. Matched on the collected_value column in the collections table.
      schema:
        type: string
      required: false
    - name: status
      x-astliteraleval: true
      in: query
      description: |
        A regex to match for the value. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
        regular expressions are accepted. Matched on the hoststatus column in the hosts table.
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



collected_subtypes_filtered = Blueprint('api2_collected_subtype_filtered', __name__)

@collected_subtypes_filtered.route("/collected/subtypes_filtered", methods=['GET'])
@collected_subtypes_filtered.route("/collected/subtypes_filtered/", methods=['GET'])
@collected_subtypes_filtered.route("/collected/subtypes_filtered/<string:ctype>", methods=['GET'])
@collected_subtypes_filtered.route("/collected/subtypes_filtered/<string:ctype>/", methods=['GET'])
def api2_collected_types_filtered(ctype="none"): 

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()
    relation_args = list()
    where_clauses = list()
    where_clause_parameters = list()
    argument_error = False
    group_value=False

    #print(ctype)

    if "ctype" in request.args :
        ctype = request.args["ctype"]

    if "usevalue" in request.args :
        group_value=True

    if "csubtype" in request.args :
        try:
            csubtype = ast.literal_eval(request.args["csubtype"])
            relation_args.append("csubtype='"+csubtype+"'")
        except Exception as e :
            error_dict["csubtype_read_error"] = "Error parsing csubtype filter" + str(e)
            argument_error=True
        else:
            this_clause = " collection_subtype REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_parameters.append(str(csubtype))

    if "hostname" in request.args :
        try:
            hostname = ast.literal_eval(request.args["hostname"])
            relation_args.append("hostname='"+hostname+"'")
        except Exception as e :
            error_dict["hostname_read_error"] = "Error parsing hostname " + str(e)
            argument_error=True
        else:
            this_clause = " hosts.hostname REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_parameters.append(str(hostname))

    if "pop" in request.args :
        try:
            print(request.args["pop"])
            pop = ast.literal_eval(request.args["pop"])
            relation_args.append("pop='"+pop+"'")
        except Exception as e :
            error_dict["pop_read_error"] = "Error parsing pop " + str(e)
            argument_error=True
        else:
            this_clause = " hosts.pop REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_parameters.append(str(pop))

    if "status" in request.args :
        try:
            print(request.args["status"])
            status = ast.literal_eval(request.args["status"])
            relation_args.append("status='"+status+"'")
        except Exception as e :
            error_dict["status_read_error"] = "Error parsing status " + str(e)
            argument_error=True
        else:
            this_clause = " hosts.hoststatus REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_parameters.append(str(status))

    if "srvtype" in request.args :
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
            relation_args.append("srvtype='"+srvtype+"'")
        except Exception as e :
            error_dict["srvtype_read_error"] = "Error parsing srvtype " + str(e)
            argument_error=True
        else:
            this_clause = " hosts.srvtype REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_parameters.append(str(srvtype))

    if "value" in request.args :
        try:
            value = ast.literal_eval(request.args["value"])
            relation_args.append("collection_value='"+value+"'")
        except Exception as e :
            error_dict["value_read_error"] = "Error parsing value " + str(e)
            argument_error=True
        else:
            this_clause = " collection_value REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_parameters.append(str(value))

    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish API Version 2 : Filtered Collected Subtypes for type " + ctype
    meta_dict["status"] = "In Progress"
    meta_dict["NOW"] = g.NOW

    if argument_error == False :
        try:
            where_clause_string = " and ".join(where_clauses)
            # To take into account the value grouping on cache
            hash_string= str(where_clause_parameters) + str(ctype) + str(group_value)
            cache_hash_object = hashlib.sha512(hash_string.encode())
            cache_string = cache_hash_object.hexdigest()
        except Exception as e :
            error_dict["cache_hash_error"] = "Error generating cache hash object" + str(e)
            print("Error " + str(e))
            argument_error = True
        else :
            meta_dict["cache_hash"] = cache_string
            meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + "/collected_subtypes_filtered_" + cache_string + ".json"

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/types"
    links_dict["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/subtypes/filtered/"

    requesttype = "collection_subtype_filtered"

    do_query = True
    #print(meta_dict)

    # Check to see if a Cache File exists
    if argument_error is False and os.path.isfile(meta_dict["this_cached_file"]) is True :
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
    if argument_error == True :
        do_query = False

    # Means that the cache file doesn't exit or isn't fresh
    if len(where_clause_string) > 0 :
        where_joiner = " and "
    else :
        where_joiner = " "

    if group_value == True :
        group_value_get = ", collection_value as value "
        group_by_string = " group by collection_subtype, collection_value "
    else :
        group_value_get = " "
        group_by_string = " group by collection_subtype "

    # Have a deterministic query so that query caching can do it's job
    where_clause_parameters.insert(0, str(ctype))
    where_clause_parameters.insert(0, str(g.twoDayTimestamp))

    # This line has been nosec'ed. All the items that are user generated are now
    # Paramaterized.
    collected_subtype_query="select distinct(collection_subtype) as subtype , count(*) as count " +\
                                group_value_get + \
                                " from collection join hosts ON fk_host_id = hosts.host_id " +\
                                " where collection.last_update >= FROM_UNIXTIME( %s ) and collection_type = %s " +\
                                where_joiner + where_clause_string + \
                                " " + group_by_string + " ; " # nosec

    if do_query :
        g.cur.execute(collected_subtype_query, where_clause_parameters)
        all_subtypes = g.cur.fetchall()
        amount_of_subtypes = len(all_subtypes)
    else :
        error_dict["do_query"] = "Query Ignored"
        amount_of_subtypes = 0

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

