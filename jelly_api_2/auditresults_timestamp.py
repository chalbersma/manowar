#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

Historical Results
/auditresults/{audit_id}/{timestamp}

Grab the historical list of servers that failed an audit at a particular time

```swagger-yaml
/auditresults/{audit_id}/{timestamp}/ :
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
        in: query
        description: |
          A regex to match for the hostname. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the hostname column in the host table.
        schema:
          type: string
        required: false
      - name: pop
        in: query
        description: |
          A regex to match for the pop name. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the pop column in the host table.
        schema:
          type: string
        required: false
      - name: srvtype
        in: query
        description: |
          A regex to match for the srvtype name. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the srvtype column in the host table.
        schema:
          type: string
        required: false
      - name: bucket
        in: query
        description: |
          A regex to match for the bucket name. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the bucket column in the audits_by_host table.
        schema:
          type: string
        required: false
      - name: auditResult
        in: query
        description: |
          A regex to match for the audit result.. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the audit_result column in the audits_by_host table.
          Audit result is stored as an enum so best values are "pass", "fail" or "notafflicted".
        schema:
          type: string
        required: false
      - name: auditResultText
        in: query
        description: |
          A regex to match for the Audit Result text (generally the failing version).
          [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the audit_result_text column in the audits_by_host table.
        schema:
          type: string
        required: false
      - name: status
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

auditresults_timestamp = Blueprint('api2_auditresults_timestamp', __name__)


@auditresults_timestamp.route("/auditresults/<int:audit_id>/<int:request_timestamp>", methods=['GET'])
@auditresults_timestamp.route("/auditresults/<int:audit_id>/<int:request_timestamp>/", methods=['GET'])
def api2_auditresults_timestamp(request_timestamp=0, audit_id=0):
    '''
    Return the Audit Results as they appeared at a particular time.
    '''

    args_def = args_def = {"audit_id": {"req_type": int,
                                        "default": audit_id,
                                        "required": True,
                                        "sql_param": True,
                                        "sql_clause": "fk_audits_id = %s",
                                        "positive": True},
                           "request_timestamp": {"req_type": int,
                                                 "default": request_timestamp,
                                                 "required": True,
                                                 "sql_param": True,
                                                 "sql_param_count": 2,
                                                 "sql_clause": "initial_audit <= FROM_UNIXTIME( %s ) and last_audit >= FROM_UNIXTIME( %s )",
                                                 "positive": True}
                           }

    args = db_helper.process_args(args_def,
                                  request.args,
                                  include_hosts_sql=True,
                                  include_ar_sql=True,
                                  include_exact=True)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 Audit Results for Audit ID " + \
        str(audit_id) + " at time " + str(request_timestamp)
    meta_dict["status"] = "In Progress"

    links_dict["parent"] = "{}{}/auditresults?".format(g.config_items["v2api"]["preroot"],
                                                       g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/auditresults/{}/{}?{}".format(g.config_items["v2api"]["preroot"],
                                                             g.config_items["v2api"]["root"],
                                                             args["audit_id"],
                                                             args["request_timestamp"],
                                                             args["qdeparsed_string"])

    requesttype = "auditresults_timestamp"

    audit_result_ts_query = '''select audit_result_id, audits.audit_name, fk_host_id, hosts.hostname, fk_audits_id,
                                    UNIX_TIMESTAMP(initial_audit) as 'initial_audit', UNIX_TIMESTAMP(last_audit) as 'last_audit',
                                    bucket, audit_result, audit_result_text, hosts.pop, hosts.srvtype
                                    from audits_by_host
                                    join hosts on fk_host_id = host_id
                                    join audits on fk_audits_id = audit_id
                                    where {}
                                    group by fk_host_id
                                    '''.format(" and ".join(args["args_clause"]))

    results = db_helper.run_query(g.cur,
                                  audit_result_ts_query,
                                  args=args["args_clause_args"],
                                  one=False,
                                  do_abort=True,
                                  require_results=False)

    for this_result in results.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_result["fk_host_id"]
        this_results["attributes"] = this_result
        this_results["auditinfo"] = this_result["audit_result_id"]
        this_results["relationships"] = dict()

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
