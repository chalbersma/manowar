#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/cve/canoncial_check/{cve_name}/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Gives you a check against a particular cve for the population you specify
      in the arguments. Accepts the non collection paramaters (as this utilizes
      the collection paramaters) to make the check.
    tags:
      - cve
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
```
"""

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import time
import hashlib
import os
import urllib
import requests

cve_canonical_check = Blueprint('api2_cve_canonical_check', __name__)


@cve_canonical_check.route("/cve/canonical_check", methods=['GET'])
@cve_canonical_check.route("/cve/canonical_check/", methods=['GET'])
@cve_canonical_check.route("/cve/canonical_check/<string:cve_name>", methods=['GET'])
@cve_canonical_check.route("/cve/canonical_check/<string:cve_name>/", methods=['GET'])
def api2_cve_canonical_check(cve_name=None, hostname=False, pop=False, srvtype=False,
                             hoststatus=False, status=False, exact=False):

    # TODO Modernize This (Possibly Removal)

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Canonical CVE Information for Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()
    meta_info["glc_Endpoint"] = list()
    error_dict = dict()

    global_population_query_args = dict()

    argument_error = False

    if "cve_name" in request.args:
        try:
            cve_name = ast.literal_eval(request.args["cve_name"])
        except Exception as e:
            argument_error = True
            error_dict["cve_parse_error"] = "Can not parse cve"

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
                global_population_query_args["exact"] = "True"

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
            global_population_query_args["hostname"] = "'{}'".format(hostname)

    if "pop" in request.args:
        try:
            pop = ast.literal_eval(request.args["pop"])
        except Exception as e:
            error_dict["pop_parse_error"] = "Could not parse pop." + str(e)
            argument_error = True
        else:
            global_population_query_args["pop"] = pop

    if "srvtype" in request.args:
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
        except Exception as e:
            error_dict["srvtype_parse_error"] = "Could not parse srvtype." + \
                str(e)
            argument_error = True
        else:
            global_population_query_args["srvtype"] = "'{}'".format(srvtype)

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
        global_population_query_args["hoststatus"] = "'{}'".format(hoststatus)

    requesttime = time.time()

    requesttype = "canonical_cve_check"

    links_info = dict()

    links_info["self"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/cve/canonical_check/"
    links_info["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/cve/"
    links_info["children"] = dict()

    request_data = list()

    # Hash Request For Caching
    if argument_error == False:
        try:
            query_tuple = (cve_name, exact, hostname, pop, srvtype, hoststatus)
            meta_info["query_tuple"] = query_tuple
            query_string = str(query_tuple)
            cache_hash_object = hashlib.sha1(query_string.encode())  # nosec
            cache_string = cache_hash_object.hexdigest()
        except Exception as e:
            error_dict["cache_hash_error"] = "Error generating cache hash object" + \
                str(e)
            argument_error = True
        else:
            meta_info["cache_hash"] = cache_string

    if argument_error == False:
        meta_info["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + \
            "/cve_check_" + cache_string + ".json"

    if argument_error == False and os.path.isfile(meta_info["this_cached_file"]) is True:
        # There's a Cache File see if it's fresh
        cache_file_stats = os.stat(meta_info["this_cached_file"])
        # Should be timestamp of file in seconds
        cache_file_create_time = int(cache_file_stats.st_ctime)
        if cache_file_create_time > g.MIDNIGHT:
            # Cache is fresh as of midnight
            with open(meta_info["this_cached_file"]) as cached_data:
                try:
                    cached = json.load(cached_data)
                except Exception as e:
                    print("Error reading cache file: " +
                          meta_info["this_cached_file"] + " with error " + str(e))
                else:
                    return jsonify(**cached)

    do_query = True

    # Select Query
    if do_query and argument_error == False:
        this_cve_data = shuttlefish(cve=cve_name)
    else:
        error_dict["do_query"] = "Query Ignored"
        this_cve_data = False

    this_cve_data

    if this_cve_data != False:

        if this_cve_data.get("priority", "Untriaged") in ["Untriaged"]:
            # Ignore
            meta_info["cve_checked"] = False
            cve_check_results = dict()
        else:
            rel_dict = dict()

            # print(this_cve_data["packages"].keys())
            for pkg_name in this_cve_data["packages"].keys():
                this_pkg_obj = this_cve_data["packages"][pkg_name]
                for release in this_pkg_obj["releases"].keys():
                    this_pkg_release_obj = this_pkg_obj["releases"][release]

                    # Create Dict
                    if release not in rel_dict.keys():
                        rel_dict[release] = dict()
                        rel_dict[release]["packages_to_check"] = False
                        rel_dict[release]["pending_patches"] = False
                        rel_dict[release]["packages_pending_release"] = list()

                    if this_pkg_release_obj["status"] in ["needed", "needs-triage"]:
                        rel_dict[release]["pending_patches"] = True
                        rel_dict[release]["packages_pending_release"].append(
                            pkg_name)

                    if this_pkg_release_obj["status"] in ["released"]:
                        # At least one to check against.
                        pkg_value = this_pkg_release_obj["version"]

                        # In theory you could key off of ctype, csubtype, mvalue or mtype here
                        if "mtype" not in rel_dict[release].keys():
                            # Do initial hydration, this is the first package
                            rel_dict[release]["packages_to_check"] = True
                            rel_dict[release]["ctype"] = list()
                            rel_dict[release]["csubtype"] = list()
                            rel_dict[release]["mvalue"] = list()
                            rel_dict[release]["mtype"] = "aptge"

                        rel_dict[release]["ctype"].append("packages")
                        rel_dict[release]["csubtype"].append(pkg_name)
                        rel_dict[release]["mvalue"].append(pkg_value)

            meta_info["cve_check_data"] = rel_dict

            # Now I've a releas dictionary that has all of the items that I need to do
            # a genericlargecompare against the endpoint.

            cve_check_results = dict()

            for release in rel_dict.keys():

                if rel_dict[release]["packages_to_check"] == False:
                    # Nothing to see here, move along
                    pass
                else:
                    # Something to Check!
                    generic_large_compare_query = g.config_items["v2api"]["root"] + \
                        "/genericlargecompare/?"

                    local_args = {"matchcollection_pop": "True",
                                  "matchcollection_ctype": "'release'",
                                  "matchcollection_csubtype": "'default'",
                                  "matchcollection_cvalue": "'{}'".format(release),
                                  "ctype": rel_dict[release]["ctype"],
                                  "csubtype": rel_dict[release]["csubtype"],
                                  "mtype": "'{}'".format(rel_dict[release]["mtype"]),
                                  "mvalue": rel_dict[release]["mvalue"]}

                    # Python3.5 + Syntax
                    #this_query_args = { **local_args, **global_population_query_args }

                    this_query_args = local_args.copy()
                    this_query_args.update(global_population_query_args)

                    query_string = urllib.parse.urlencode(this_query_args)

                    glc_private = "{}{}{}".format(
                        g.HTTPENDPOINT, generic_large_compare_query, query_string)

                    content = requests.get(glc_private)

                    content_json = content.json()

                    meta_info["glc_Endpoint"].append("{}{}{}".format(str(
                        g.config_items["v2api"]["preroot"]), generic_large_compare_query, query_string))

                    if "errors" in content_json.keys():
                        meta_info["release_error"] = "Errors getting releases for {}.".format(
                            release)
                        found_hosts = 0
                        results_array = list()
                    else:
                        results_array = [
                            hostdict for hostdict in content_json["data"]]
                        found_hosts = len(results_array)

                    cve_check_results[release] = dict()
                    cve_check_results[release]["results"] = results_array
                    cve_check_results[release]["count"] = found_hosts

        request_data = cve_check_results

    if this_cve_data != False and len(request_data.keys()) > 0:

        response_dict = dict()

        response_dict = dict()
        response_dict["meta"] = meta_info
        response_dict["data"] = request_data
        response_dict["links"] = links_info

        try:
            with open(meta_info["this_cached_file"], 'w') as cache_file_object:
                json.dump(response_dict, cache_file_object)
        except Exception as e:
            print("Error writing file " +
                  str(meta_info["this_cached_file"]) + " with error " + str(e))
        else:
            pass
            #print("Cache File wrote to " + str(meta_info["this_cached_file"]) + " at timestamp " + str(g.NOW))

        return jsonify(**response_dict)
    else:
        return jsonify(meta=meta_info, errors=error_dict, links=links_info)
