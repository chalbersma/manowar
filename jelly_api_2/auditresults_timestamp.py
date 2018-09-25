#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

Historical Results
/auditresults/{audit_id}/{timestamp}

Grab the historical list of servers that failed an audit at a particular time

```swagger-yaml
/auditresults/{audit_id}/{timestamp}/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Designed to grab a list of hosts that either pass or fail an audit
      along with the relevant data about each host. Similar to the auditresults
      endpoint, except that this one also takes a timestamp so that it can
      return the results as it appears at a particular time.
    responses:
      200:
        description: OK
    parameters:
      - name: audit_id
        in: path
        description: |
          The id of the audit you wish to get hosts back for. Needs to be speicied here or
          in the query string. This parameter is not technically required.
        schema:
          type: integer
        required: true
      - name: timestamp
        in: path
        description: |
          A Unix Timestamp that you want to check for the date against.
          Must be a positive integer. This variable is required. If you
          wish to get the "latest" you shoul utilize the /auditresults
          endpoint.
        schema:
          type: integer
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
      - name: bucket
        x-astliteraleval: true
        in: query
        description: |
          A regex to match for the bucket name. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the bucket column in the audits_by_host table.
        schema:
          type: string
        required: false
      - name: auditResult
        x-astliteraleval: true
        in: query
        description: |
          A regex to match for the audit result.. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the audit_result column in the audits_by_host table.
          Audit result is stored as an enum so best values are "pass", "fail" or "notafflicted".
        schema:
          type: string
        required: false
      - name: auditResultText
        x-astliteraleval: true
        in: query
        description: |
          A regex to match for the Audit Result text (generally the failing version).
          [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the audit_result_text column in the audits_by_host table.
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

auditresults_timestamp = Blueprint('api2_auditresults_timestamp', __name__)

@auditresults_timestamp.route("/auditresults/<int:audit_id>/<int:request_timestamp>", methods=['GET'])
@auditresults_timestamp.route("/auditresults/<int:audit_id>/<int:request_timestamp>/", methods=['GET'])
def api2_auditresults_timestamp(request_timestamp=0, audit_id=0, hostname=False, pop=False, srvtype=False, bucket=False, auditResult=False, auditResultText=False, status=False):
    # Stuff

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    where_clauses = list()
    where_clause_args = list()

    # Grab Values
    if "audit_id" in request.args :
        try:
            audit_id = ast.literal_eval(request.args["audit_id"])
        except Exception as e :
            #print("Exception")
            error_dict["audit_id_read_error"] = "Error parsing audit_id " + str(e)
            argument_error=True

    if "request_timestamp" in request.args :
        try:
            request_timestamp = ast.literal_eval(request.args["request_timestamp"])
        except Exception as e :
            #print("Exception")
            error_dict["request_timestamp_read_error"] = "Error parsing request_timestamp " + str(e)
            argumenent_error=True



    if argument_error == False :
        if type(audit_id) is int and audit_id > 0 :
            audit_where_clause = " fk_audits_id = %s "
            where_clause_args.append(str(audit_id))
        else :
            error_dict["audit_id_type_error"] = "Audit_ID isn't a positive integer : " + str(e) + ". Shame on you."
            argument_error=True

        if type(request_timestamp) is int and request_timestamp > 0 :
            # Find only requests that meet our specifications.
            timestamp_where_clause = " initial_audit <= FROM_UNIXTIME( %s ) and last_audit >= FROM_UNIXTIME( %s ) "
        else :
            error_dict["request_timestamp_type_error"] = "request_timestamp isn't a positive integer : " + str(e) + ". Do you even time bro?"



    #print(audit_id)
    #print(argument_error)
    #print(audit_where_clause)

    # Grab Additional Values
    if "hostname" in request.args :
        try:
            hostname = ast.literal_eval(request.args["hostname"])
        except Exception as e :
            error_dict["hostname_read_error"] = "Error parsing hostname " + str(e)
            argument_error=True
        else:
            this_clause = " hosts.hostname REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_args.append(str(hostname))

    if "pop" in request.args :
        try:
            pop = ast.literal_eval(request.args["pop"])
        except Exception as e :
            error_dict["pop_read_error"] = "Error parsing pop " + str(e)
            argument_error=True
        else:
            this_clause = " hosts.pop REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_args.append(str(pop))

    if "status" in request.args :
        try:
            status = ast.literal_eval(request.args["status"])
        except Exception as e :
            error_dict["status_read_error"] = "Error parsing status " + str(e)
            argument_error=True
        else:
            this_clause = " hosts.hoststatus REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_args.append(str(status))

    if "srvtype" in request.args :
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
        except Exception as e :
            error_dict["srvtype_read_error"] = "Error parsing srvtype " + str(e)
            argument_error=True
        else:
            this_clause = " hosts.srvtype REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_args.append(str(srvtype))

    if "bucket" in request.args :
        try:
            bucket = ast.literal_eval(request.args["bucket"])
        except Exception as e :
            error_dict["bucket_read_error"] = "Error parsing bucket " + str(e)
            argument_error=True
        else:
            this_clause = " bucket REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_args.append(str(bucket))

    if "auditResult" in request.args :
        try:
            auditResult = ast.literal_eval(request.args["auditResult"])
        except Exception as e :
            error_dict["auditResult_read_error"] = "Error parsing auditResult " + str(e)
            argument_error=True
        else:
            this_clause = " audit_result REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_args.append(str(auditResult))

    if "auditResultText" in request.args :
        try:
            auditResultText = ast.literal_eval(request.args["auditResultText"])
        except Exception as e :
            error_dict["auditResultText_read_error"] = "Error parsing auditResultText " + str(e)
            argument_error=True
        else:
            this_clause = " audit_result_text REGEXP %s "
            where_clauses.append(this_clause)
            where_clause_args.append(str(auditResultText))

    # Hash Request For Caching
    if argument_error == False :
        try:
            where_clause_string = " and ".join(where_clauses)

            my_query_string = where_clause_string + " and " + timestamp_where_clause
            hash_string = str(where_clause_args) + " and " + timestamp_where_clause

            # timestamp_where_clause uses 2 timestamp
            where_clause_args.append(request_timestamp)
            where_clause_args.append(request_timestamp)

            cache_hash_object = hashlib.sha1(hash_string.encode()) # nosec
            cache_string = cache_hash_object.hexdigest()
        except Exception as e:
            error_dict["cache_hash_error"] = "Error generating cache hash object" + str(e)
            argument_error = True
        else:
            meta_dict["cache_hash"] = cache_string


    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish API Version 2 Audit Results for Audit ID " + str(audit_id) + " at time " + str(request_timestamp)
    meta_dict["status"] = "In Progress"

    if argument_error == False :
        meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + "/auditresults_timestamp_" + str(audit_id) + "_#" + str(cache_string) + ".json"


    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditresults"
    links_dict["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditresults/{audit_id}/{request_timestamp}"

    requesttype = "auditresults_timestamp"

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
        audit_result_query_head="select audit_result_id, audits.audit_name, fk_host_id, hosts.hostname, fk_audits_id, "
        audit_result_query_head = audit_result_query_head +\
                                    " UNIX_TIMESTAMP(initial_audit) as 'initial_audit', UNIX_TIMESTAMP(last_audit) as 'last_audit', " +\
                                    " bucket, audit_result, audit_result_text, hosts.pop, hosts.srvtype" +\
                                    " from audits_by_host " +\
                                    " join hosts on fk_host_id = host_id " +\
                                    " join audits on fk_audits_id = audit_id "

        if len(where_clause_string) > 0 :
            where_joiner = " and "
        else :
            where_joiner = " "

        audit_result_query_where=" where " + audit_where_clause + where_joiner + my_query_string
        audit_result_query_tail=" group by fk_host_id "

        audit_result_query = audit_result_query_head + audit_result_query_where + audit_result_query_tail

    if do_query and argument_error == False :
        #print(audit_result_query)
        g.cur.execute(audit_result_query, where_clause_args)
        all_hosts = g.cur.fetchall()
        amount_of_hosts = len(all_hosts)
    else :
        error_dict["do_query"] = "Query Ignored"
        amount_of_hosts = 0

    if amount_of_hosts > 0 :
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_hosts)) :
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = all_hosts[i]["fk_host_id"]
            this_results["attributes"] = all_hosts[i]
            this_results["auditinfo"] = all_hosts[i]["audit_result_id"]
            this_results["relationships"] = dict()
            this_results["relationships"]["auditinfo"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditinfo/" + str(all_hosts[i]["fk_host_id"])

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
