#!/usr/bin/env python3

'''
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

Historical Results
/auditresults/{audit_id}/range/{backdays}

Grab the historical amount of results for an audit.

```swagger-yaml
/auditresults/{audit_id}/range/{backdays}/ :
  get:
    description: |
      Designed to grab a list of hosts that either pass or fail an audit
      along with the relevant data about each host. Similar to the auditresults
      endpoint, except that this one also takes a timestamp so that it can
      return the results as it appears at a particular time.
    responses:
      200:
        description: OK
    tags:
      - audits
    parameters:
      - name: audit_id
        in: path
        description: |
          The id of the audit you wish to get hosts back for. Needs to be speicied here or
          in the query string. This parameter is not technically required.
        schema:
          type: integer
        required: true
      - name: backdays
        in: path
        description: |
          How many days back to look. This will use the last Midnight time and go back from
          there.
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
from datetime import date, timezone

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory, abort

import manoward

auditresults_range = Blueprint('api2_auditresults_range', __name__)


@auditresults_range.route("/auditresults/<int:audit_id>/range/<int:backdays>", methods=['GET'])
@auditresults_range.route("/auditresults/<int:audit_id>/range/<int:backdays>/", methods=['GET'])
def api2_auditresults_range(backdays=0, audit_id=0):
    '''
    Get the Results going Back backdays number of days
    '''

    args_def = args_def = {"audit_id": {"req_type": int,
                                        "default": audit_id,
                                        "required": True,
                                        "sql_param": True,
                                        "sql_clause": "fk_audits_id = %s",
                                        "positive": True},
                           "backdays": {"req_type": int,
                                        "default": backdays,
                                        "required": True,
                                        "sql_param": False,
                                        "positive": True},
                           }

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_hosts_sql=True,
                                 include_ar_sql=True,
                                 include_exact=True)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 Counts Results over a range for a particular type {} for {} days".format(args["audit_id"],
                                                                                                                          args["backdays"])
    meta_dict["status"] = "In Progress"

    requesttype = "auditresults_range"
    links_dict["parent"] = "{}{}/auditresults/{}?{}".format(g.config_items["v2api"]["preroot"],
                                                            g.config_items["v2api"]["root"],
                                                            args["audit_id"],
                                                            args["qdeparsed_string"])

    links_dict["self"] = "{}{}/auditresults/{}/range/{}?{}".format(g.config_items["v2api"]["preroot"],
                                                                   g.config_items["v2api"]["root"],
                                                                   args["audit_id"],
                                                                   args["backdays"],
                                                                   args["qdeparsed_string"])

    # Generate a List of Timestamps to Cycle Through
    check_timestamps = list()

    for x in range(args["backdays"], 0, -1):
        this_timestamp_to_add = g.MIDNIGHT - (x * 86400)

        this_date_object = date.fromtimestamp(this_timestamp_to_add)

        this_date_string = this_date_object.strftime('%m-%d')

        check_timestamps.append(
            [this_date_string, this_timestamp_to_add, this_timestamp_to_add, this_timestamp_to_add])

    audit_result_query = '''select %s as date, count(*) as hosts, '%s' as timestamp
                               from ( select * from audits_by_host
                               join hosts on fk_host_id = host_id
                               join audits on fk_audits_id = audit_id
                               where {}
                               and initial_audit <= FROM_UNIXTIME(%s)
                               and last_audit >= FROM_UNIXTIME(%s)
                               group by fk_host_id ) as this_hosts
                               '''.format(" and ".join(args["args_clause"]))

    # Build my Arguments List
    query_args = [[timestamp[0], timestamp[1], *args["args_clause_args"],
                   timestamp[2], timestamp[3]] for timestamp in check_timestamps]

    run_result = manoward.run_query(g.cur,
                                    audit_result_query,
                                    args=query_args,
                                    one=False,
                                    do_abort=True,
                                    require_results=True,
                                    many=True)

    for this_day_result in run_result.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_day_result["timestamp"]
        this_results["attributes"] = this_day_result
        this_results["relationships"] = dict()
        this_results["relationships"]["auditinfo"] = "{}{}/auditinfo/{}".format(g.config_items["v2api"]["preroot"],
                                                                                g.config_items["v2api"]["root"],
                                                                                args["audit_id"])

        this_results["relationships"]["auditresults_timestamp"] = "{}{}/auditresults/{}/{}?{}".format(g.config_items["v2api"]["preroot"],
                                                                                                      g.config_items["v2api"]["root"],
                                                                                                      args["audit_id"],
                                                                                                      this_day_result["timestamp"],
                                                                                                      args.get("qdeparsed_string", ""))

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
