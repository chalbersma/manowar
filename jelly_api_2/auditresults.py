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
    tags:
      - audits
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
    {{ ar | indent(6, True) }}
    {{ hosts | indent(6, True) }}
    {{ exact | indent(6, True) }}
```

'''

import json
import ast
import time
import os
import hashlib

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory, abort

import manoward

auditresults = Blueprint('api2_auditresults', __name__)


@auditresults.route("/auditresults/", methods=['GET'])
@auditresults.route("/auditresults/<int:audit_id>", methods=['GET'])
@auditresults.route("/auditresults/<int:audit_id>/", methods=['GET'])
def api2_auditresults(audit_id=0):
    '''
    Return the Audit Results for Particular Audit filtered by
    A series of Items.
    '''

    args_def = args_def = {"audit_id": {"req_type": int,
                                        "default": audit_id,
                                        "required": True,
                                        "sql_param": True,
                                        "sql_clause": "fk_audits_id = %s",
                                        "positive": True},
                           }

    args = manoward.process_args(args_def, request.args, include_hosts_sql=True,
                                 include_ar_sql=True,
                                 include_exact=True, abh_limit=g.twoDayTimestamp)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()

    requesttype = "auditresults"
    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 Audit Results for Audit ID {}".format(
        args["audit_id"])
    meta_dict["status"] = "In Progress"

    links_dict["parent"] = "{}{}".format(g.config_items["v2api"]["preroot"],
                                         g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/auditresults/{}?{}".format(g.config_items["v2api"]["preroot"],
                                                          g.config_items["v2api"]["root"],
                                                          args["audit_id"],
                                                          args["qdeparsed_string"])

    audit_result_query = '''select audit_result_id, audits.audit_name, fk_host_id, fk_audits_id,
                            UNIX_TIMESTAMP(initial_audit) as 'initial_audit', UNIX_TIMESTAMP(last_audit) as 'last_audit',
                            bucket, audit_result, audit_result_text, {}
                            from audits_by_host
                            join hosts on fk_host_id = host_id
                            join audits on fk_audits_id = audit_id
                            where {}'''.format(" , ".join(g.host_data_columns),
                                               " and ".join(args["args_clause"]))

    results = manoward.run_query(g.cur,
                                 audit_result_query,
                                 args=args["args_clause_args"],
                                 one=False,
                                 do_abort=True,
                                 require_results=False)

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
