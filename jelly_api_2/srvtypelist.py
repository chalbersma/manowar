#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/srvtypelist/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Gives a list of srvtypes found in the environment
    responses:
      200:
        description: OK
    parameters:
      - name: srvtype_name
        in: query
        description: |
            Regex to search against for the pops.
        schema:
          type: string
      - name: with_pop
        in: query
        description: |
            Only with Pops that meet this criteria.
        schema:
          type: string
      - name: with_hostname
        in: query
        description: |
            Only with Hostnames that meet this criteria.
        schema:
          type: string
      - name: with_status
        in: query
        description: |
            Only with Status that meet this criteria.
        schema:
          type: string
      - name: exact
        in: query
        description: |
            Don't Use Regexs, instead use exact matching.
        schema:
          type: string


```
"""

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import time
import hashlib
import os


srvtypelist = Blueprint('api2_srvtypelist', __name__)

@srvtypelist.route("/srvtypelist", methods=['GET'])
@srvtypelist.route("/srvtypelist/", methods=['GET'])
def api2_srvtypelist(srvtype_name=None, with_pop=None, with_hostname=None, with_status=None, exact=False):

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Srvtype List for Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()


    error_dict = dict()

    argument_error = False
    where_args = list()
    where_args_params = list()

    # Add Default Timestamp
    where_args.append("last_update >= FROM_UNIXTIME( %s )")
    where_args_params.append(str(g.twoDayTimestamp))

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

    if "srvtype_name" in request.args :
        try:
            srvtype_name_regex = ast.literal_eval(request.args["srvtype_name"])
        except Exception as e :
            argument_error = True
            error_dict["srvtype_name_parse_error"] = "Can not parse srvtype_name"
        else:
            where_args_params.append(srvtype_name_regex)
            if useRegex :
                where_args.append(" hosts.srvtype REGEXP %s ")
            else :
                # Use exact matching
                where_args.append(" hosts.srvtype = %s ")


    if "with_pop" in request.args :
        try:
            pop_regex = ast.literal_eval(request.args["with_pop"])
        except Exception as e :
            argument_error = True
            error_dict["with_srvtype_parse_error"] = "Can not parse with_pop"
        else:
            where_args_params.append(pop_regex)
            if useRegex :
                where_args.append(" hosts.pop REGEXP %s ")
            else :
                # Use exact matching
                where_args.append(" hosts.pop = %s ")

    if "with_hostname" in request.args :
        try:
            hostname_regex = ast.literal_eval(request.args["with_hostname"])
        except Exception as e :
            argument_error = True
            error_dict["with_hostname_parse_error"] = "Can not parse with_hostname"
        else:
            where_args_params.append(hostname_regex)
            if useRegex :
                where_args.append(" hosts.hostname REGEXP %s ")
            else :
                # Use exact matching
                where_args.append(" hosts.hostname = %s ")

    if "with_status" in request.args :
        try:
            status_regex = ast.literal_eval(request.args["with_status"])
        except Exception as e :
            argument_error = True
            error_dict["with_status_parse_error"] = "Can not parse with_status"
        else:
            where_args_params.append(status_regex)
            if useRegex :
                where_args.append(" hosts.hoststatus REGEXP %s ")
            else :
                # Use exact matching
                where_args.append(" hosts.hoststatus = %s ")



    requesttime=time.time()

    requesttype = "srvtype_list"

    links_info = dict()

    links_info["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/srvtypelist"
    links_info["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/"
    links_info["children"] = dict()

    request_data = list()

    # Hash Request For Caching
    if argument_error == False :
        try:
            query_tuple = ( useRegex, srvtype_name, with_pop, with_status, with_hostname )
            meta_info["query_tuple"] = query_tuple
            query_string = str(query_tuple)
            cache_hash_object = hashlib.sha1(query_string.encode()) # nosec
            cache_string = cache_hash_object.hexdigest()
        except Exception as e:
            error_dict["cache_hash_error"] = "Error generating cache hash object" + str(e)
            argument_error = True
        else:
            meta_info["cache_hash"] = cache_string

    if argument_error == False :
        meta_info["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + "/srvtypelist_" + cache_string + ".json"

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

    if len(where_args) > 0 :
        where_joiner = " where "
        where_clause_strings = " and ".join(where_args)
        where_full_string = where_joiner + where_clause_strings
    else :
        where_full_string = " "


    srvtype_list_query='''select DISTINCT srvtype
                        from hosts '''

    srvtype_list_query = srvtype_list_query + where_full_string


    # Select Query
    if do_query and argument_error == False :
        #print(g.cur.mogrify(srvtype_list_query, where_args_params))
        g.cur.execute(srvtype_list_query, where_args_params)
        all_srvtypes = g.cur.fetchall()
        amount_of_srvtypes = len(all_srvtypes)
    else :
        error_dict["do_query"] = "Query Ignored"
        amount_of_srvtypes = 0

    if amount_of_srvtypes > 0 :
        collections_good = True
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_srvtypes)) :
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = all_srvtypes[i]["srvtype"]
            this_results["attributes"] = all_srvtypes[i]
            this_results["relationships"] = dict()
            this_results["relationships"]["hostsof"] = "{}{}/hostsearch/?srvtype='{}'&exact=True".format(g.config_items["v2api"]["preroot"],\
                                                                                                       g.config_items["v2api"]["root"],\
                                                                                                       all_srvtypes[i]["srvtype"])
            # Now pop this onto request_data
            request_data.append(this_results)

    else :
        error_dict["ERROR"] = ["No Collections"]
        collections_good = False

    if collections_good :
        return jsonify(meta=meta_info, data=request_data, links=links_info)
    else :
        return jsonify(meta=meta_info, errors=error_dict, links=links_info)

