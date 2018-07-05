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

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory
import json
import ast
import time
import os
import hashlib

hostsearch = Blueprint('api2_hostsearch', __name__)

@hostsearch.route("/hostsearch", methods=['GET'])
@hostsearch.route("/hostsearch/", methods=['GET'])
def api2_hostsearch(exact=False, hostname=False, pop=False, srvtype=False, \
                        hoststatus=False, status=False, matchcollection=False, \
                        ctype=False, csubtype=False, cvalue=False):

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    where_clauses = list()
    where_clause_args = list()

    # Add Default Timestamp
    where_clauses.append("hosts.last_update >= FROM_UNIXTIME( %s )")
    where_clause_args.append(str(g.twoDayTimestamp))

    useCollectionMatch=False
    if "matchcollection" in request.args :
        try:
            matchcollection = ast.literal_eval(request.args["matchcollection"])
        except Exception as e :
            error_dict["exact_read_error"] = "Error parsing collection_subtype " + str(e)
            argument_error=True
        else:
            if matchcollection == True :
                useCollectionMatch=True

    if "ctype" in request.args and useCollectionMatch == True :
        try:
            # Override query string for complex searches
            ctype = ast.literal_eval(request.args["ctype"])
        except Exception as e :
            error_dict["ctype_error"] = "Error parsing ctype from query string " + str(e)
            argument_error=True
        else:
            # Because of Indexing, regex isn't supported for
            # Collection types.
            where_clause_args.append(str(ctype))
            where_clauses.append(" collection.collection_type =  %s ")

    if "csubtype" in request.args and useCollectionMatch == True :
        try:
            # Override query string for complex searches
            csubtype = ast.literal_eval(request.args["csubtype"])
        except Exception as e :
            error_dict["csubtype_error"] = "Error parsing csubtype from query string " + str(e)
            argument_error=True
        else:
            # Because of Indexing, regex isn't supported for
            # Collection types.
            where_clause_args.append(str(csubtype))
            where_clauses.append(" collection.collection_subtype =  %s ")

    if "cvalue" in request.args and useCollectionMatch == True :
        try:
            # Override query string for complex searches
            cvalue = ast.literal_eval(request.args["cvalue"])
        except Exception as e :
            error_dict["cvalue_error"] = "Error parsing cvalue from query string " + str(e)
            argument_error=True
        else:
            # Because of Indexing, regex isn't supported for
            # Collection types.
            where_clause_args.append(str(cvalue))
            where_clauses.append(" collection.collection_value =  %s ")

    if useCollectionMatch == True and \
        ( cvalue == False or csubtype == False or ctype == False ):

        # Throw an erroror
        error_dict["collection_match_inputs_missing"] = "Missing some or all of the collection match inputs."
        argument_error = True


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

    # Grab Values
    if "hostname" in request.args :
        try:
            # Override query string for complex searches
            hostname = ast.literal_eval(request.args["hostname"])
        except Exception as e :
            error_dict["search read error"] = "Error parsing search from query string " + str(e)
            argument_error=True
        else:
            where_clause_args.append(str(hostname))
            if useRegex :
                where_clauses.append(" hosts.hostname REGEXP %s ")
            else :
                # Use exact matching
                where_clauses.append(" hosts.hostname = %s ")


    if "pop" in request.args :
        try:
            pop = ast.literal_eval(request.args["pop"])
        except Exception as e :
            error_dict["pop_parse_error"] = "Could not parse pop." + str(e)
            argument_error = True
        else :
            where_clause_args.append(str(pop))
            if useRegex :
                where_clauses.append(" hosts.pop REGEXP %s ")
            else :
                where_clauses.append(" hosts.pop = %s ")

    if "srvtype" in request.args :
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
        except Exception as e :
            error_dict["srvtype_parse_error"] = "Could not parse srvtype." + str(e)
            argument_error = True
        else :
            where_clause_args.append(str(srvtype))
            if useRegex :
                where_clauses.append(" hosts.srvtype REGEXP %s ")
            else :
                where_clauses.append(" hosts.srvtype = %s ")

    have_hoststatus=False
    if "hoststatus" in request.args :
        try:
            hoststatus = ast.literal_eval(request.args["hoststatus"])
        except Exception as e :
            error_dict["hoststatus_parse_error"] = "Could not parse hoststatus." + str(e)
            argument_error = True
        else :
            have_hoststatus=True
    elif "status" in request.args :
        # Allow hoststatus override
        try:
            # Override
            hoststatus = ast.literal_eval(request.args["status"])
        except Exception as e :
            error_dict["hoststatus_parse_error"] = "Could not parse hoststatus." + str(e)
            argument_error = True
        else :
            have_hoststatus=True
    if have_hoststatus :
        where_clause_args.append(str(hoststatus))
        if useRegex :
            where_clauses.append(" hosts.hoststatus REGEXP %s ")
        else :
            where_clauses.append(" hosts.hoststatus = %s ")


    # Hash Request For Caching
    if argument_error == False :
        try:
            query_tuple = ( useRegex, hostname , pop, srvtype, hoststatus, matchcollection, ctype, csubtype, cvalue)
            meta_dict["query_tuple"] = query_tuple
            query_string = str(query_tuple)
            cache_hash_object = hashlib.sha1(query_string.encode())
            cache_string = cache_hash_object.hexdigest()
        except Exception as e:
            error_dict["cache_hash_error"] = "Error generating cache hash object" + str(e)
            argument_error = True
        else:
            meta_dict["cache_hash"] = cache_string

        meta_dict["version"]  = 2
        meta_dict["name"] = "Jellyfish API Version 2 Host Search results for " + str(query_tuple)
        meta_dict["status"] = "In Progress"

    if argument_error == False :
        meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + "/hostquery_" + cache_string + ".json"


    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/"
    links_dict["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/hostsearch"

    requesttype = "hostquery"

    do_query = True

    #print(meta_dict, argument_error)

    # Check to see if a Cache File exists
    if argument_error == False and os.path.isfile(meta_dict["this_cached_file"]) is True  :
        # There's a Cache File see if it's fresh
        cache_file_stats = os.stat(meta_dict["this_cached_file"])
        ## Should be timestamp of file in seconds
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

        if useCollectionMatch == True :
            join_bits = " join collection on host_id = collection.fk_host_id "
        else :
            join_bits = " "

        host_search_args = where_clause_args
        where_clause = " and ".join(where_clauses)
        # Query is paramaterized and is not vulnerable to SQL injection
        host_search = '''select host_id, host_uber_id, hostname, pop, srvtype, hoststatus, UNIX_TIMESTAMP(hosts.last_update) as last_update from hosts
                        {}
                        where
                        '''.format(join_bits) # nosec

        host_search = host_search + where_clause

        #print(host_search)
        #print(host_search_args)

    if do_query and argument_error == False :
        #print(g.cur.mogrify(host_search, host_search_args))
        g.cur.execute(host_search, host_search_args)
        found_hosts = g.cur.fetchall()
    else :
        error_dict["do_query"] = "Query Ignored"
        found_hosts = list()


    if len(found_hosts) > 0 :
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(found_hosts)) :
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = found_hosts[i]["host_id"]
            this_results["attributes"] = found_hosts[i]

            # Now pop this onto request_data
            request_data.append(this_results)

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
            # No need to write a log file about this.
            #print("Cache File wrote to " + str(meta_dict["this_cached_file"]) + " at timestamp " + str(g.NOW))

        return jsonify(**response_dict)
    else :

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
