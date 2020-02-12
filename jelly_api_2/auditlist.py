#!/usr/bin/env python3

"""
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/auditlist/ :
  get:
    description: |
      Get the Dashboard information about.
    tags:
      - audits
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

import json
import ast
import time

from flask import current_app, Blueprint, g, request, jsonify, abort

import manoward

auditlist = Blueprint('api2_auditlist', __name__)


@auditlist.route("/auditlist", methods=['GET'])
@auditlist.route("/auditlist/", methods=['GET'])
def api2_auditlist(audit_name=None, audit_priority=None, audit_description=None, audit_long_description=None):
    '''
    List out All the Audits that meet the Items Prescribed
    '''

    # TODO add exact definitions
    args_def = {"audit_name": {"req_type": str,
                               "default": audit_name,
                               "required": False,
                               "sql_param": True,
                               "sql_clause": "audit_name REGEXP %s",
                               "qdeparse": True},
                "audit_description": {"req_type": str,
                                      "default": audit_description,
                                      "required": False,
                                      "sql_param": True,
                                      "sql_clause": "audit_short_description REGEXP %s",
                                      "qdeparse": True},
                "audit_priority": {"req_type": str,
                                   "default": audit_priority,
                                   "required": False,
                                   "sql_param": True,
                                   "sql_clause": "audit_priority REGEXP %s",
                                   "qdeparse": True},
                "audit_long_description": {"req_type": str,
                                           "default": audit_long_description,
                                           "required": False,
                                           "sql_param": True,
                                           "sql_clause": "audit_long_description REGEXP %s",
                                           "qdeparse": True},
                }

    args = manoward.process_args(args_def, request.args)

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Audit List for Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()

    requesttype = "audit_list"

    links_info = dict()

    links_info["self"] = "{}{}/auditlist?{}".format(g.config_items["v2api"]["preroot"],
                                                    g.config_items["v2api"]["root"],
                                                    args.get("qdeparsed_string", ""))

    links_info["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_info["children"] = dict()

    request_data = list()

    if len(args["args_clause_args"]) > 0:
        where_joiner = " where "
        where_clause_strings = " and ".join(args["args_clause"])
        where_full_string = where_joiner + where_clause_strings
    else:
        where_full_string = " "

    audit_list_query = '''select audit_id, audit_name, audit_priority,
                            audit_short_description, audit_primary_link
                            from audits '''

    audit_list_query = audit_list_query + where_full_string

    results = manoward.run_query(g.cur,
                                 audit_list_query,
                                 args=args["args_clause_args"],
                                 one=False,
                                 do_abort=True,
                                 require_results=True)

    for this_audit in results.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_audit["audit_id"]
        this_results["attributes"] = this_audit
        this_results["relationships"] = dict()
        this_results["relationships"]["auditinfo"] = "{}{}/auditinfo/{}".format(g.config_items["v2api"]["preroot"],
                                                                                g.config_items["v2api"]["root"],
                                                                                this_audit["audit_id"])

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_info, data=request_data, links=links_info)
