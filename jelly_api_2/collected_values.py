#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/collected/values endpoint
Designed to grab information about information as it exists on the edge
(according to our latest collected data). 
* Returns a list of types on the server.

```swagger-yaml
/collected/values/{ctype}/{csubtype}/ : 
  x-cached-length: "Every Midnight"
  get:
    description: |
      Grabs information on host collections as it exists on the edge (according
      to our latest collected data). This query can be intensive so it is cached
      daily.
    responses:
      200:
        description: OK
    parameters:
      - name: ctype
        in: path
        description: |
          The Collection Type you wish to match against. Must be equal to this item.
          You can get a list of collection types from the `/collection/type/` endpoint.
          Can be overrriden by query string parameter.
        schema:
          type: string
        required: true
      - name: csubtype
        in: path
        description: |
           The Collection Subtype you wish to match against. Must be equal to this item.
           You can get a list of collection subtypes for a particular type from the
           `/collection/subtype/$ctype` endpoint. Can be overrdiden by query string parameter.
        schema:
          type: string
        required: true
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
      - name: exact
        x-astliteraleval: true
        in: query
        description: |
          Essentially make everything above change from a regex to an exact match instead.
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




collected_values = Blueprint('api2_collected_values', __name__)

@collected_values.route("/collected/values", methods=['GET'])
@collected_values.route("/collected/values/", methods=['GET'])
@collected_values.route("/collected/values/<string:ctype>", methods=['GET'])
@collected_values.route("/collected/values/<string:ctype>/", methods=['GET'])
@collected_values.route("/collected/values/<string:ctype>/<string:csubtype>", methods=['GET'])
@collected_values.route("/collected/values/<string:ctype>/<string:csubtype>/", methods=['GET'])
def api2_collected_values(ctype="none", csubtype="none", exact=False):

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()
    relation_args = list()
    where_clauses = list()
    where_clause_args = list()
    argument_error = False

    if "ctype" in request.args :
        ctype = ast.literal_eval(request.args["ctype"])

    if "csubtype" in request.args :
        csubtype = ast.literal_eval(request.args["csubtype"])

    useRegex=True
    if "exact" in request.args :
        try:
            exact = ast.literal_eval(request.args["exact"])
        except Exception as e :
            error_dict["exact_read_error"] = "Error parsing collection_subtype " + str(e)
            argument_error=True
        else:
            if exact == True :
                useRegex=False

    if "hostname" in request.args :
        try:
            hostname = ast.literal_eval(request.args["hostname"])
            relation_args.append("hostname='"+hostname+"'")
        except Exception as e :
            error_dict["hostname_read_error"] = "Error parsing hostname " + str(e)
            argument_error=True
        else:
            where_clause_args.append(hostname)
            if useRegex == True :
                this_clause = " hosts.hostname REGEXP %s "
            else :
                this_clause = " hosts.hostname = %s "

            where_clauses.append(this_clause)

    if "status" in request.args :
        try:
            status = ast.literal_eval(request.args["status"])
            relation_args.append("status='"+status+"'")
        except Exception as e :
            error_dict["hostname_read_error"] = "Error parsing status " + str(e)
            argument_error=True
        else:
            where_clause_args.append(status)
            if useRegex == True :
                this_clause = " hosts.hoststatus REGEXP %s "
            else :
                this_clause = " hosts.hoststatus = %s "

            where_clauses.append(this_clause)

    if "pop" in request.args :
        try:
            pop = ast.literal_eval(request.args["pop"])
            relation_args.append("pop='"+pop+"'")
        except Exception as e :
            error_dict["pop_read_error"] = "Error parsing pop " + str(e)
            argument_error=True
        else:
            this_clause = " hosts.pop REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_args.append(pop)

    if "srvtype" in request.args :
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
            relation_args.append("srvtype='"+srvtype+"'")
        except Exception as e :
            error_dict["srvtype_read_error"] = "Error parsing srvtype " + str(e)
            argument_error=True
        else:
            where_clause_args.append(srvtype)

            if useRegex == True :
                this_clause = " hosts.srvtype REGEXP %s "
            else :
                this_clause = " hosts.srvtype = %s "

            where_clauses.append(this_clause)

    if "value" in request.args :
        try:
            value = ast.literal_eval(request.args["value"])
            relation_args.append("collection_value='"+value+"'")
        except Exception as e :
            error_dict["value_read_error"] = "Error parsing value " + str(e)
            argument_error=True
        else:
            where_clause_args.append(value)
            if useRegex == True :
                this_clause = " collection_value REGEXP %s "
            else :
                this_clause = " collection_value = %s "

            where_clauses.append(this_clause)


    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish API Version 2 : Collected values for type " + str(ctype) + " and subtype " + str(csubtype)
    meta_dict["status"] = "In Progress"
    meta_dict["NOW"] = g.NOW

    if argument_error == False :
        try:
            where_clause_string = " and ".join(where_clauses)
            hash_string=str(where_clause_args)+ctype+csubtype+str(useRegex)
            cache_hash_object = hashlib.sha512(hash_string.encode())
            cache_string = cache_hash_object.hexdigest()
        except Exception as e :
            error_dict["cache_hash_error"] = "Error generating cache hash object" + str(e)
            argument_error = True
        else :
            meta_dict["cache_hash"] = cache_string
            meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + "/collected_values_" + cache_string + ".json"

    links_dict["children"] = { "types" : ( g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/values" ) }
    links_dict["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/subtypes"
    links_dict["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/values"

    requesttype = "collected_value"

    do_query = True

    # Check to see if a Cache File exists
    if argument_error == False and os.path.isfile(meta_dict["this_cached_file"]) is True :
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

    if argument_error == False :
        # Where Joiners
        if len(where_clause_string) > 0 :
            where_joiner = " and "
        else :
            where_joiner = " "

        # Have a deterministic query so that query caching can do it's job
        collected_values_query_head="SELECT collection_id, hosts.host_id, hosts.hostname, hosts.hoststatus,  hosts.pop, hosts.srvtype, collection_type, collection_subtype, collection_value, UNIX_TIMESTAMP(collection.initial_update) as initial_update, UNIX_TIMESTAMP(collection.last_update) as last_update FROM collection JOIN hosts ON fk_host_id = hosts.host_id "
        collected_values_query_tail=" where collection.last_update >= FROM_UNIXTIME(%s) and collection_type = %s and collection_subtype = %s " + \
                                        where_joiner + where_clause_string + " ; "

        collected_values_query = collected_values_query_head + collected_values_query_tail

        collected_values_args = [ str(g.twoDayTimestamp), str(ctype), str(csubtype) ]
        collected_values_args.extend(where_clause_args)

    else :
        do_query = True

    if do_query :
        g.cur.execute(collected_values_query, collected_values_args)
        #print(g.cur._last_executed)
        all_values = g.cur.fetchall()
        amount_of_values = len(all_values)
    else :
        error_dict["do_query"] = "Query Ignored"
        amount_of_values = 0

    if amount_of_values > 0 :
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_values)) :
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = all_values[i]["collection_id"]
            this_results["attributes"] = all_values[i]

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
            pass
            #print("Cache File wrote to " + str(meta_dict["this_cached_file"]) + " at timestamp " + str(g.NOW))


        return jsonify(**response_dict)
    else :

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)

    
