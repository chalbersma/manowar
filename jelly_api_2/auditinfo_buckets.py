#!/usr/bin/env python3

'''
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

auditinfo/<audit_id>/buckets

Gives you the information about comparisons & filters for this particular
audit. Utilize the "filename" column of the audits table & then loads in
that particular file. Depends on the filename existing on both the host
that runs the audits and the part that displays the audits

```swagger-yaml
/auditinfo/{audit_id}/buckets/ :
  get:
    description: |
      Get's the bucket information for a particular audit. Does not retrieve
      The data from the database because of limitations. Instead retrieves it
      from "on disk." This means that what is returned here may not be as
      accurate as it could be.
    tags:
      - audits
    responses:
      200:
        description: OK
    parameters:
      - name: audit_id
        in: path
        description: |
          The id of the audit's buckets you desire. You need to either specify it in path or optionally
          in the query string.
        schema:
          type: integer
        required: true
```

'''

import json
import ast
import time

from flask import current_app, Blueprint, g, request, jsonify, abort
import audittools
import manoward


auditinfo_buckets = Blueprint('api2_auditinfo_buckets', __name__)


@auditinfo_buckets.route("/auditinfo/<int:audit_id>/buckets", methods=['GET'])
@auditinfo_buckets.route("/auditinfo/<int:audit_id>/buckets/", methods=['GET'])
def api2_auditinfo_buckets(audit_id=0):
    '''
    Loads the Audit Definition from Disk and Reads in the Arbitrarily Complex
    Audit Filters and Comparisons to Provide the Needed Data
    '''

    requesttype = "Audit Buckets"

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Audit Bucket Information."
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()

    links_info = dict()

    links_info["self"] = "{}{}/auditinfo/{}/buckets".format(g.config_items["v2api"]["preroot"],
                                                            g.config_items["v2api"]["root"],
                                                            audit_id)

    links_info["parent"] = "{}{}/auditinfo/{}/".format(g.config_items["v2api"]["preroot"],
                                                       g.config_items["v2api"]["root"],
                                                       audit_id)
    links_info["children"] = dict()

    request_data = list()

    select_query = '''select filename, audit_name from audits where audit_id = %s order by
                    audit_priority desc, audit_id desc '''

    if audit_id <= 0:
        g.logger.error("Zero or Negative Bucket ID Given")
        abort(404)

    run_result = manoward.run_query(g.cur,
                                    select_query,
                                    args=[audit_id],
                                    one=True,
                                    do_abort=True,
                                    require_results=True)

    requested_audit = run_result.get("data", dict())

    audit = dict()
    audit["id"] = audit_id
    audit["type"] = requesttype
    audit["relationships"] = dict()
    audit["relationships"]["auditinfo"] = "{}{}/auditinfo/{}/".format(g.config_items["v2api"]["preroot"],
                                                                      g.config_items["v2api"]["root"],
                                                                      audit_id)
    audit["attributes"] = dict()

    #
    # Now Load File
    #

    try:
        this_audit_config = audittools.load_auditfile(
            requested_audit["filename"])
    except Exception as audit_error:
        g.logger.error("Unable to Parse Data from Auditfile : {}".format(
            requested_audit["filename"]))
        g.logger.debug(audit_error)
        abort(500)

    if requested_audit["audit_name"] not in this_audit_config.keys():
        g.logger.error("Unable to Find Audit Described in File.")
        g.logger.debug("Available Audits in file {} : {}".format(requested_audit["filename"],
                                                                 this_audit_config.keys()))
        abort(404)

    audit["attributes"]["filters"] = this_audit_config[requested_audit["audit_name"]]["filters"]
    audit["attributes"]["comparisons"] = this_audit_config[requested_audit["audit_name"]]["comparisons"]

    request_data.append(audit)

    return jsonify(meta=meta_info, data=request_data, links=links_info)
