#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/auditlist/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Get the Dashboard information about.
    responses:
      200:
        description: OK
    parameters:
      - name: audit_name
        in: query
        description: |
            Regex to search against for audits.
        schema:
          type: string
      - name: audit_priority
        in: query
        description: |
            Regex describing what audit priorities should be returned.
        schema:
          type: string
      - name: audit_description
        in: query
        description: |
            Looking for your string in the audit short description.
        schema:
          type: string
      - name: audit_long_description
        in: query
        description: |
            Looking for your string in the audit long description.
        schema:
          type: string

```
"""

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import time


auditlist = Blueprint('api2_auditlist', __name__)

@auditlist.route("/auditlist", methods=['GET'])
@auditlist.route("/auditlist/", methods=['GET'])
def api2_auditlist(audit_name=None, audit_priority=None, audit_description=None, audit_long_description=None):

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Audit List for Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()


    error_dict = dict()

    argument_error = False
    where_args = list()
    where_args_params = list()

    if "audit_name" in request.args :
        try:
            audit_name_regex = ast.literal_eval(request.args["audit_name"])
        except Exception as e :
            argument_error = True
            error_dict["audit_name_parse_error"] = "Can not parse audit_name"
        else:
            where_args.append(" audit_name REGEXP %s ")
            where_args_params.append(audit_name_regex)

    if "audit_priority" in request.args :
        try:
            audit_priority_regex = ast.literal_eval(request.args["audit_priority"])
        except Exception as e :
            argument_error = True
            error_dict["audit_priority_parse_error"] = "Cannot parse audit_priority"
        else:
            where_args.append(" audit_priority REGEXP %s ")
            where_args_params.append(audit_priority_regex)

    if "audit_description" in request.args:
        try:
            audit_description_regex = ast.literal_eval(request.args["audit_description"])
        except Exception as e:
            argument_error = True
            error_dict["audit_description_parse_error"] = "Cannot parse audit_desription"
        else :
            where_args.append(" audit_short_description REGEXP %s ")
            where_args_params.append(audit_description_regex)

    if "audit_long_description" in request.args:
        try:
            audit_long_description_regex = ast.literal_eval(request.args["audit_long_description"])
        except Exception as e:
            argument_error = True
            error_dict["audit_long_description_parse_error"] = "Cannot parse audit_long_description"
        else :
            where_args.append(" audit_long_description REGEXP %s ")
            where_args_params.append(audit_long_description_regex)

    requesttime=time.time()

    requesttype = "audit_list"

    meta_info["request_tuple"] = ( audit_name, audit_priority, audit_description, audit_long_description )

    links_info = dict()

    links_info["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditlist"
    links_info["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/"
    links_info["children"] = dict()

    request_data = list()

    do_query = True

    if len(where_args_params) > 0 :
        where_joiner = " where "
        where_clause_strings = " and ".join(where_args)
        where_full_string = where_joiner + where_clause_strings
    else :
        where_full_string = " "


    audit_list_query='''select audit_id, audit_name, audit_priority,
                            audit_short_description, audit_primary_link
                            from audits '''

    audit_list_query = audit_list_query + where_full_string


    # Select Query
    if do_query and argument_error == False :
        g.cur.execute(audit_list_query, where_args_params)
        all_audits = g.cur.fetchall()
        amount_of_audits = len(all_audits)
    else :
        error_dict["do_query"] = "Query Ignored"
        amount_of_audits = 0

    if amount_of_audits > 0 :
        collections_good = True
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_audits)) :
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = all_audits[i]["audit_id"]
            this_results["attributes"] = all_audits[i]
            this_results["relationships"] = dict()
            this_results["relationships"]["auditinfo"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditinfo/" + str(all_audits[i]["audit_id"])

            # Now pop this onto request_data
            request_data.append(this_results)
    else :
        error_dict["ERROR"] = ["No Collections"]
        collections_good = False

    if collections_good :
        return jsonify(meta=meta_info, data=request_data, links=links_info)
    else :
        return jsonify(meta=meta_info, errors=error_dict, links=links_info)

