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
    tags:
      - audits
    parameters:
      - name: collatedType
        in: path
        description: |
          The type of collated value that you wish to see. Initially can only be pop,
          srvtype or acoll (For audit). In the future may include more collations if
          additional collations are added.
        schema:
          type: string
          enum: [pop, srvtype, acoll]
        required: true
      - name: typefilter
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
        in: query
        description: |
          An audit ID to check against. Will filter results to just the auditID that you're interested in. For example, specifying
          7 with a collatedType of "pop" will lead to all of the pops returning their pass/fail/exempt amounts for auditID #7.
        schema:
          type: string
        required: false
```
'''

import json
import ast
import time
import os
import hashlib

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory, abort

import manoward

collated = Blueprint('api2_collated', __name__)


@collated.route("/collated/", methods=['GET'])
@collated.route("/collated/<collatedType>", methods=['GET'])
@collated.route("/collated/<collatedType>/", methods=['GET'])
def api2_collated(collatedType=False, typefilter=False, auditID=False):

    args_def = {"collatedType": {"req_type": str,
                                 "default": collatedType,
                                 "required": True,
                                 "sql_param": False,
                                 "qdeparse": False,
                                 "enum": ("pop", "srvtype", "acoll")},
                "auditID": {"req_type": int,
                            "default": None,
                            "required": False,
                            "sql_param": True,
                            "sql_clause": "audits_by_{}.fk_audits_id = %s".format(collatedType),
                            "qdeparse": True},
                "typefilter": {"req_type": str,
                               "default": None,
                               "required": False,
                               "sql_param": True,
                               "sql_clause": "audits_by_{}.{}_text REGEXP %s ".format(collatedType, collatedType),
                               "qdeparse": True}
                }

    args = manoward.process_args(args_def, request.args)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 Collated Resultsfor " + \
        str(collatedType)
    meta_dict["status"] = "In Progress"

    links_dict["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/collated/{}/?{}".format(g.config_items["v2api"]["preroot"],
                                                       g.config_items["v2api"]["root"],
                                                       collatedType,
                                                       args["qdeparsed_string"])

    requesttype = "collated"

    # Add the Time Limitation
    args["args_clause"].append(
        "{}_last_audit >= FROM_UNIXTIME( %s )".format(collatedType))
    args["args_clause_args"].append(g.twoDayTimestamp)

    collated_query = '''select {0}_id, {0}_text, fk_audits_id, audits.audit_name,
                            UNIX_TIMESTAMP({0}_initial_audit) as {0}_initial_audit,
                            UNIX_TIMESTAMP( {0}_last_audit ) as {0}_last_audit,
                            {0}_passed, {0}_failed, {0}_exempt
                            FROM audits_by_{0}
                            JOIN audits on audits.audit_id = fk_audits_id
                            WHERE {1}
                            GROUP BY {0}_text, fk_audits_id'''.format(collatedType,
                                                                      " and ".join(args["args_clause"]))

    results = manoward.run_query(g.cur,
                                 collated_query,
                                 args=args["args_clause_args"],
                                 one=False,
                                 do_abort=True,
                                 require_results=False)

    for this_csult in results.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_csult["{}_id".format(collatedType)]
        this_results["attributes"] = this_csult
        this_results["relationships"] = dict()

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
