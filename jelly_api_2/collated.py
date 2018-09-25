#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/collated endpoints. Designed to return info about audit by audit, pop & srvtype.
Accepts a regex filter for the main name

```swagger-yaml
/collated/{collatedType}/ :
  get:
    description: |
      Returns data that get's collated in the collate module. Can get results deliminated by audit for audits
      ( yes you can get audits by audit ), pops & srvtypes.
    responses:
      200:
        description: OK
    parameters:
      - name: collatedType
        in: path
        description: |
          The type of collated value that you wish to see. Initially can only be pop,
          srvtype or acoll (For audit). In the future may include more collations if
          additional collations are added.
        schema:
          type: string
        required: true
      - name: typefilter
        x-astliteraleval: true
        in: query
        description: |
          A regex to match for the collated type (pop, srvtype or audit). [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the $collatedType column of the table in question. Should be encased in
          parenthesis as it's evaluated by [ast.literal_eval](https://docs.python.org/3.6/library/ast.html) on the backend as
          part of it's sanitization.
        schema:
          type: string
        required: false
      - name: auditID
        x-astliteraleval: true
        in: query
        description: |
          An audit ID to check against. Will filter results to just the auditID that you're interested in. For example, specifying
          7 with a collatedType of "pop" will lead to all of the pops returning their pass/fail/exempt amounts for auditID #7.
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

collated = Blueprint('api2_collated', __name__)

@collated.route("/collated/", methods=['GET'])
@collated.route("/collated/<collatedType>", methods=['GET'])
@collated.route("/collated/<collatedType>/", methods=['GET'])
def api2_collated(collatedType=False, typefilter=False, auditID=False):

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    where_clauses = list()
    where_clause_parameters = list()
    available_collatedType=["pop", "srvtype", "acoll"]

    # Grab Values
    if "collatedType" in request.args :
        try:
            collatedType = ast.literal_eval(request.args["collatedType"])
        except Exception as e :
            print("Exception")
            error_dict["collatedType_read_error"] = "Error parsing collatedType " + str(e)
            argument_error=True
    if argument_error == False :
        if type(collatedType) is str and collatedType in available_collatedType :
            table_name = "audits_by_" + collatedType
        else :
            error_dict["collatedType_error"] = "collatedType isn't a string or not in the accepted table list : " + str(collatedType) + ". Shame on you."
            argument_error=True

    # Grab Additional Values
    if "typefilter" in request.args :
        try:
            typefilter = ast.literal_eval(request.args["typefilter"])
        except Exception as e :
            error_dict["typefilter_read_error"] = "Error parsing typefilter " + str(e)
            argument_error=True
        else:
            this_clause = " audits_by_{}.{}_text REGEXP %s ".format(collatedType, collatedType)
            where_clauses.append(this_clause)
            where_clause_parameters.append(typefilter)

    # Audit ID
    if "auditID" in request.args :
        try:
            auditID = ast.literal_eval(request.args["auditID"])
        except Exception as e :
            error_dict["auditID_read_error"] = "Error parsing auditID " + str(e)
            argument_error=True
        else:
            if type(auditID) is int and auditID > 0 :
                this_clause = " audits_by_" + collatedType + ".fk_audits_id = %s "
                where_clauses.append(this_clause)
                where_clause_parameters.append(auditID)
            else :
                error_dict["auditID_type_error"] = "AuditID " + str(auditID) + "Isn't a positive integer."
                argument_error=True

    query_tuple = ( collatedType, typefilter, auditID )

    # Hash Request For Caching
    if argument_error == False :
        try:
            hash_string=str(query_tuple)
            cache_hash_object = hashlib.sha1(hash_string.encode()) # nosec
            cache_string = cache_hash_object.hexdigest()
        except Exception as e:
            error_dict["cache_hash_error"] = "Error generating cache hash object" + str(e)
            argument_error = True
        else:
            meta_dict["cache_hash"] = cache_string

    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish API Version 2 Collated Resultsfor " + str(collatedType)
    meta_dict["status"] = "In Progress"

    if argument_error == False :
        meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + "/collated_" + cache_string + ".json"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/"

    requesttype = "collated"

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

        # Insert Paramaters
        where_clauses.append("{}_last_audit >= FROM_UNIXTIME( %s ) ".format(str(collatedType)))
        where_clause_parameters.append(str(g.twoDayTimestamp) )

        if len(where_clauses) > 0 :
            where_clause_string = " and ".join(where_clauses)
        else :
            where_clause_string = " "


        # No Secced input for columns is validate in line 70
        # Redesign this to be multiple selects.
        collated_result_query= "SELECT "  +\
                                collatedType + "_id, " +\
                                collatedType + "_text, " +\
                                "fk_audits_id, " +\
                                "audits.audit_name, " +\
                                "UNIX_TIMESTAMP( {}_initial_audit ) as {}_initial_audit , ".format(collatedType, collatedType) +\
                                "UNIX_TIMESTAMP( {}_last_audit ) as {}_last_audit , ".format(collatedType, collatedType) +\
                                collatedType + "_passed, " +\
                                collatedType + "_failed, " +\
                                collatedType + "_exempt " +\
                                "FROM " +\
                                " audits_by_" + collatedType +\
                                " JOIN " +\
                                " audits ON audits.audit_id = fk_audits_id " +\
                                "WHERE " +\
                                where_clause_string +\
                                " GROUP BY " + collatedType + "_text, fk_audits_id " # nosec

    if do_query and argument_error == False :
        #print(g.cur.mogrify(collated_result_query, where_clause_parameters))
        g.cur.execute(collated_result_query, where_clause_parameters)
        all_results = g.cur.fetchall()
        howmany = len(all_results)
    else :
        error_dict["do_query"] = "Query Ignored"
        howmany = 0

    if howmany > 0 :
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_results)) :
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = all_results[i][(collatedType + "_id")]
            this_results["attributes"] = all_results[i]
            this_results["relationships"] = dict()

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


