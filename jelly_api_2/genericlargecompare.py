#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

API for Host Information
Should return data about the host & return the collections for this particular host.

```swagger-yaml
/genericlargecompare/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Generic Large Commparison against a particular hoststatus.
    responses:
      200:
        description: OK
    tags:
      - liveaudit
    parameters:
      - name: hostname
        in: query
        description: |
          The regex the hostname you wish to get data for.
        schema:
          type: integer
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
      - name: matchcollection_pop
        in: query
        description: |
          Uses hoststatu's matchcollection feature to match a collection
        schema:
          type: string
        required: false
      - name: matchcollection_ctype
        in: query
        description: |
          Uses hostsearch ctype match
        schema:
          type: string
        required: false
      - name: matchcollection_csubtype
        in: query
        description: |
          Uses hostsearch csubtype match
        schema:
          type: string
        required: false
      - name: matchcollection_cvalue
        in: query
        description: |
          Uses hostsearch cvalue match
        schema:
          type: string
        required: false
      - name: mtype
        in: query
        description: |
          What type of match you should do. Can be any of the non subtype comparisons
          noted in the docs.
        schema:
          type: string
        required: false
      - name: ctype
        in: query
        description: |
          What collection type of match you should do your match against. Put this
          in as an array or I'll get angry at ya.
        schema:
          type: array
        required: false
      - name: csubtype
        in: query
        description: |
          What collection sub type of match you should do your match against. Put this
          in as an array or I'll get angry at ya.
        schema:
          type: array
        required: false
      - name: mvalue
        in: query
        description: |
            What collection value shoudl I match against. THis is an array.
        schema:
          type: array
        required: false

```
'''

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory
import json
import ast
import time
import os
import hashlib
import urllib
import requests
from manoward.generic_large_compare import generic_large_compare
#import apt

genericlargecompare = Blueprint('api2_genericlargecompare', __name__)


@genericlargecompare.route("/genericlargecompare", methods=['GET'])
@genericlargecompare.route("/genericlargecompare/", methods=['GET'])
def api2_genericlargecompare(exact=False, hostname=False, pop=False, srvtype=False,
                             hoststatus=False, status=False, matchcollection_pop=False,
                             matchcollection_ctype=False, matchcollection_csubtype=False,
                             matchcollection_cvalue=False, mtype=False, ctype=False,
                             csubtype=False, mvalue=False, fresh=172800):

    # TODO Reconsider If this is a Wise Move.

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    where_clauses = list()
    where_clause_args = list()

    # Add Default Timestamp
    population_query_args = dict()

    useCollectionMatch = False
    if "matchcollection_pop" in request.args:
        try:
            matchcollection_pop = ast.literal_eval(
                request.args["matchcollection_pop"])
        except Exception as e:
            error_dict["exact_read_error"] = "Error parsing collection_subtype " + \
                str(e)
            argument_error = True
        else:
            if matchcollection_pop == True:
                useCollectionMatch = True
                population_query_args["matchcollection"] = "True"

    if "matchcollection_ctype" in request.args and useCollectionMatch == True:
        try:
            # Override query string for complex searches
            matchcollection_ctype = ast.literal_eval(
                request.args["matchcollection_ctype"])
        except Exception as e:
            error_dict["matchcollection_ctype_error"] = "Error parsing matchcollection_ctype from query string " + \
                str(e)
            argument_error = True
        else:
            # Because of Indexing, regex isn't supported for
            # Collection types.
            population_query_args["ctype"] = "'{}'".format(
                str(matchcollection_ctype))

    if "matchcollection_csubtype" in request.args and useCollectionMatch == True:
        try:
            # Override query string for complex searches
            matchcollection_csubtype = ast.literal_eval(
                request.args["matchcollection_csubtype"])
        except Exception as e:
            error_dict["matchcollection_csubtype_error"] = "Error parsing matchcollection_csubtype from query string " + \
                str(e)
            argument_error = True
        else:
            # Because of Indexing, regex isn't supported for
            # Collection types.
            population_query_args["csubtype"] = "'{}'".format(
                str(matchcollection_csubtype))

    if "matchcollection_cvalue" in request.args and useCollectionMatch == True:
        try:
            # Override query string for complex searches
            matchcollection_cvalue = ast.literal_eval(
                request.args["matchcollection_cvalue"])
        except Exception as e:
            error_dict["matchcollection_cvalue_error"] = "Error parsing matchcollection_cvalue from query string " + \
                str(e)
            argument_error = True
        else:
            # Because of Indexing, regex isn't supported for
            # Collection types.
            population_query_args["cvalue"] = "'{}'".format(
                str(matchcollection_cvalue))

    if useCollectionMatch == True and \
            (matchcollection_cvalue == False or matchcollection_csubtype == False or matchcollection_ctype == False):
        argument_error = True

    if "mtype" in request.args:
        try:
            mtype = ast.literal_eval(request.args["mtype"])
        except Exception as e:
            error_dict["mtype_read_error"] = "Error parsing mtype " + str(e)
            argument_error = True
        else:
            # Do type checking
            if type(mtype) is list:
                argument_error = True
                error_dict["mtype_futures_error"] = "Mtype array values not."
            if type(mtype) is not str:
                argument_error = True
                error_dict["mtype_type_unknown"] = "Mtype type unknown."
    else:
        error_dict["mtype_required"] = "Match Type not found in query string."
        argument_error = True

    if "ctype" in request.args:
        try:
            ctype = ast.literal_eval(request.args["ctype"])
        except Exception as e:
            error_dict["ctype_read_error"] = "Error parsing collection type " + \
                str(e)
            argument_error = True
        else:
            if type(ctype) is not list:
                argument_error = True
                error_dict["ctype_type_unknown"] = "Ctype type unknown."
    else:
        error_dict["ctype_required"] = "ctype not found in query string."
        argument_error = True

    if "csubtype" in request.args:
        try:
            csubtype = ast.literal_eval(request.args["csubtype"])
        except Exception as e:
            error_dict["csubtype_read_error"] = "Error parsing collection subtype " + \
                str(e)
            argument_error = True
        else:
            if type(csubtype) is not list:
                argument_error = True
                error_dict["csubtype_type_unknown"] = "Csubtype type unknown."
    else:
        error_dict["csubtype_required"] = "csubtype not found in query string."
        argument_error = True

    if "mvalue" in request.args:
        try:
            mvalue = ast.literal_eval(request.args["mvalue"])
        except Exception as e:
            error_dict["mvalue_read_error"] = "Error parsing match value " + \
                str(e)
            argument_error = True
        else:
            if type(mvalue) is not list:
                argument_error = True
                error_dict["mvalue_type_unknown"] = "MValue type unknown."
    else:
        error_dict["mvalue_required"] = "mvalue not found in query string."
        argument_error = True

    if "fresh" in request.args:
        try:
            fresh = ast.literal_eval(request.args["fresh"])
        except Exception as e:
            error_dict["exact_read_error"] = "Error parsing collection_subtype " + \
                str(e)
            argument_error = True
        else:
            if type(fresh) is int and fresh > 0:
                pass
            else:
                argument_error = True
                error_dict["invalid_fresh_argument"] = "Fresh Argument."

    useRegex = True
    if "exact" in request.args:
        try:
            exact = ast.literal_eval(request.args["exact"])
        except Exception as e:
            error_dict["exact_read_error"] = "Error parsing collection_subtype " + \
                str(e)
            argument_error = True
        else:
            if exact == True:
                population_query_args["exact"] = "True"

    # Grab Values
    if "hostname" in request.args:
        try:
            # Override query string for complex searches
            hostname = ast.literal_eval(request.args["hostname"])
        except Exception as e:
            error_dict["search read error"] = "Error parsing search from query string " + \
                str(e)
            argument_error = True
        else:
            population_query_args["hostname"] = "'{}'".format(hostname)

    if "pop" in request.args:
        try:
            pop = ast.literal_eval(request.args["pop"])
        except Exception as e:
            error_dict["pop_parse_error"] = "Could not parse pop." + str(e)
            argument_error = True
        else:
            population_query_args["pop"] = pop

    if "srvtype" in request.args:
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
        except Exception as e:
            error_dict["srvtype_parse_error"] = "Could not parse srvtype." + \
                str(e)
            argument_error = True
        else:
            population_query_args["srvtype"] = "'{}'".format(srvtype)

    have_hoststatus = False
    if "hoststatus" in request.args:
        try:
            hoststatus = ast.literal_eval(request.args["hoststatus"])
        except Exception as e:
            error_dict["hoststatus_parse_error"] = "Could not parse hoststatus." + \
                str(e)
            argument_error = True
        else:
            have_hoststatus = True
    elif "status" in request.args:
        # Allow hoststatus override
        try:
            # Override
            hoststatus = ast.literal_eval(request.args["hoststatus"])
        except Exception as e:
            error_dict["hoststatus_parse_error"] = "Could not parse hoststatus." + \
                str(e)
            argument_error = True
        else:
            have_hoststatus = True
    if have_hoststatus:
        population_query_args["hoststatus"] = "'{}'".format(hoststatus)

    # Hash Request For Caching
    if argument_error == False:
        try:

            query_tuple = (exact, hostname, pop, srvtype,
                           hoststatus, status, matchcollection_pop,
                           matchcollection_ctype, matchcollection_csubtype,
                           matchcollection_cvalue, mtype, ctype,
                           csubtype, mvalue, fresh)

            meta_dict["query_tuple"] = query_tuple
            query_string = str(query_tuple)
            # Sha1 used as a unique id it's fine if you can reverse it.
            cache_hash_object = hashlib.sha1(query_string.encode())  # nosec
            cache_string = cache_hash_object.hexdigest()
        except Exception as e:
            error_dict["cache_hash_error"] = "Error generating cache hash object" + \
                str(e)
            argument_error = True
        else:
            meta_dict["cache_hash"] = cache_string

        meta_dict["version"] = 2
        meta_dict["name"] = "Jellyfish API Version 2 Generic Large Comparison results for " + \
            str(query_tuple)
        meta_dict["status"] = "In Progress"

    if argument_error == False:
        meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + \
            "/glargecompare_" + cache_string + ".json"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/"
    links_dict["self"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/genericlargecompare"

    requesttype = "genericlargecompare"

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

        # Have a deterministic query so that query caching can do it's job

    hosts_query_good = False

    if argument_error == False and do_query == True:

        population_query = g.config_items["v2api"]["root"] + "/hostsearch/?"

        query_string = urllib.parse.urlencode(population_query_args)

        population_query_private = "{}{}{}".format(
            g.HTTPENDPOINT, population_query, query_string)

        # print(population_query_private)
        content = requests.get(population_query_private)

        content_json = content.json()

        if "errors" in content_json.keys():
            population_error = True
            error_dict["population_error"] = "Errors getting population. "
            found_hosts = 0
        else:

            # Host Array
            hosts_array = [hostdict["attributes"]
                           for hostdict in content_json["data"]]
            found_hosts = len(hosts_array)
            hosts_query_good = True

    if hosts_query_good == True and found_hosts > 0:

        comparison_results = generic_large_compare(g.db, hosts_array, mtype, ctype, csubtype,
                                                   mvalue, FRESH=fresh, exemptfail=False)

        for i in range(0, len(comparison_results)):
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = comparison_results[i]["host_id"]
            this_results["attributes"] = comparison_results[i]

            if "pfe" not in comparison_results[i].keys():
                this_results["result"] = "notafflicted"
            else:
                this_results["result"] = comparison_results[i]["pfe"]

            # Now pop this onto request_data
            request_data.append(this_results)

        collections_good = True

    else:
        error_dict["ERROR"] = ["No Collections"]
        collections_good = False
        # print("Dafuq")

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
            pass
            # No need to print evertime a cache file is written.
            #print("Cache File wrote to " + str(meta_dict["this_cached_file"]) + " at timestamp " + str(g.NOW))

        return jsonify(**response_dict)
    else:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
