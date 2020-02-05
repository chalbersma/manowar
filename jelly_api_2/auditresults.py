#!/usr/bin/env python3

'''
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/auditresults endpoint. Designed to return info about the hosts

```swagger-yaml
/auditresults/{audit_id}/ :
  get:
    description: |
      Designed to grab a list of hosts that either pass or fail an audit
      along with the relevant data about each host. Similar to the audit_table
      item from the old api.
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

import json
import ast
import time
import os
import hashlib

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory, abort

import db_helper

auditresults = Blueprint('api2_auditresults', __name__)


@auditresults.route("/auditresults/", methods=['GET'])
@auditresults.route("/auditresults/<int:audit_id>", methods=['GET'])
@auditresults.route("/auditresults/<int:audit_id>/", methods=['GET'])
def api2_auditresults(audit_id=0, hostname=None, pop=None, srvtype=None, bucket=None, auditResult=None, auditResultText=None, status=None):

    '''
    Return the Audit Results for Particular Audit filtered by
    A series of Items.
    '''

    args_def = args_def = {"audit_id": {"req_type": int,
                                        "default": audit_id,
                                        "required": True,
                                        "sql_param": True,
                                        "sql_clause": "fk_audits_id = %s"},
                           "hostname": {"req_type": str,
                                        "default": hostname,
                                        "required": False,
                                        "sql_param": True,
                                        "sql_clause": "hosts.hostname REGEXP %s"},
                           "status": {"req_type": str,
                                      "default": status,
                                      "required": False,
                                      "sql_param": True,
                                      "sql_clause": "hosts.hoststatus REGEXP %s"},
                           "pop": {"req_type": str,
                                   "default": pop,
                                   "required": False,
                                   "sql_param": True,
                                   "sql_clause": "hosts.pop REGEXP %s"},
                           "srvtype": {"req_type": str,
                                       "default": srvtype,
                                       "required": False,
                                       "sql_param": True,
                                       "sql_clause": "hosts.srvtype REGEXP %s"},
                           "bucket": {"req_type": str,
                                      "default": bucket,
                                      "required": False,
                                      "sql_param": True,
                                      "sql_clause": "bucket REGEXP %s"},
                           "auditResult": {"req_type": str,
                                           "default": auditResult,
                                           "required": False,
                                           "sql_param": True,
                                           "sql_clause": "audit_result REGEXP %s"},
                           "auditResultText": {"req_type": str,
                                               "default": auditResultText,
                                               "required": False,
                                               "sql_param": True,
                                               "sql_clause": "audit_result_text REGEXP %s"},
                           }

    args = db_helper.process_args(args_def, request.args)

    if args["audit_id"] <= 0:
        g.logger.error("Invalid Audit ID")
        abort(404)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()

    requesttype = "auditresults"
    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 Audit Results for Audit ID {}".format(args["audit_id"])
    meta_dict["status"] = "In Progress"

    links_dict["parent"] = "{}{}".format(g.config_items["v2api"]["preroot"],
                                         g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/auditresults/{}".format(g.config_items["v2api"]["preroot"],
                                                       g.config_items["v2api"]["root"],
                                                       args["audit_id"])

    audit_result_query = '''select audit_result_id, audits.audit_name, fk_host_id, hosts.hostname, fk_audits_id,
                            audit_result_query_head + " UNIX_TIMESTAMP(initial_audit) as 'initial_audit', UNIX_TIMESTAMP(last_audit) as 'last_audit',
                            bucket, audit_result, audit_result_text, hosts.pop, hosts.srvtype, hosts.hoststatus
                            from audits_by_host
                            join hosts on fk_host_id = host_id
                            join audits on fk_audits_id = audit_id
                            where {}
                            and last_audit >= FROM_UNIXTIME( %s )'''.format(" and ".join(args["arg_clause"]))

    results = db_helper.run_query(g.cur,
                                  audit_result_query,
                                  args=[*args["arg_clause_args"], g.twoDayTimestamp],
                                  one=False,
                                  do_abort=True,
                                  require_results=True)

    for this_a_result in results.get("data", list()):

        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_a_result["fk_host_id"]
        this_results["attributes"] = this_a_result
        this_results["auditinfo"] = this_a_result["audit_result_id"]
        this_results["relationships"] = dict()
        this_results["relationships"]["hostinfo"] = "{}{}/hostcollections/{}".format(g.config_items["v2api"]["preroot"],
                                                                                     g.config_items["v2api"]["root"],
                                                                                     this_a_result["fk_host_id"])

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
