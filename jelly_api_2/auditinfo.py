#!/usr/bin/env python3

"""
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.


```swagger-yaml
/auditinfo/{audit_id}/ :
  get:
    description: |
      Get's the stored information about a given audit. Does not include the Bucket or Match Logic
      as there is currently a bug about those items.
    tags:
      - audits
    responses:
      200:
        description: OK
    parameters:
      - name: audit_id
        in: path
        description: |
          The id of the audit you wish to see. You need to either specify it in path or optionally
          in the query string. This parameter is not technically required. There is not good way to document
          this in swagger.
        required: true
        schema:
          type: integer
```

"""

import json
import ast
import time
from flask import current_app, Blueprint, g, request, jsonify, abort

import manoward


auditinfo = Blueprint("api2_auditinfo", __name__)


@auditinfo.route("/auditinfo", methods=["GET"])
@auditinfo.route("/auditinfo/", methods=["GET"])
@auditinfo.route("/auditinfo/<int:audit_id>", methods=["GET"])
@auditinfo.route("/auditinfo/<int:audit_id>/", methods=["GET"])
def api2_auditinfo(audit_id=0):
    '''
    Returns the Audit Information for the given Audit ID
    '''

    args_def = {"audit_id": {"required": True,
                             "default": audit_id,
                             "req_type": int,
                             "positive": True}}

    args = manoward.process_args(args_def, request.args)

    requesttype = "Audit Details"

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Audit Information Endpoint for Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()

    links_info = dict()

    links_info["self"] = "{}{}/auditinfo/{}".format(g.config_items["v2api"]["preroot"],
                                                    g.config_items["v2api"]["root"],
                                                    args["audit_id"])

    links_info["parent"] = "{}{}".format(g.config_items["v2api"]["preroot"],
                                         g.config_items["v2api"]["root"])

    links_info["children"] = dict()

    links_info["children"]["Audit Buckets"] = "{}{}/auditinfo/{}/buckets".format(g.config_items["v2api"]["preroot"],
                                                                                 g.config_items["v2api"]["root"],
                                                                                 args["audit_id"])

    request_data = list()

    select_query = """select audit_id, audit_name, audit_priority,
                            audit_short_description, audit_long_description,
                            audit_primary_link,
                            COLUMN_JSON(audit_secondary_links) as 'audit_secondary_links'
                            from audits
                            where audit_id = %s
                            order by audit_priority desc, audit_id desc ;"""

    run_result = manoward.run_query(g.cur,
                                    select_query,
                                    args=[args["audit_id"]],
                                    one=True,
                                    do_abort=True,
                                    require_results=True)

    if run_result["has_error"] is True:
        g.logger.error("Error in Auditinfo Query")
        abort(500)

    requested_audit = run_result.get("data", dict())

    # Parse audit_secondary_links back to JSON
    try:
        this_secondary_links = json.loads(
            requested_audit["audit_secondary_links"])

    except Exception as unhydrate_secondary_links_error:
        g.logger.error(
            "Unable to Read Audit Secondary Links on {}".format(args["audit_id"]))
        g.logger.debug(unhydrate_secondary_links_error)
        g.logger.debug(requested_audit["audit_secondary_links"])
        abort(500)
    else:
        requested_audit["audit_secondary_links"] = this_secondary_links

    this_results = dict()
    this_results["type"] = requesttype
    this_results["id"] = requested_audit["audit_id"]
    this_results["attributes"] = requested_audit
    this_results["relationships"] = dict()
    this_results["relationships"]["auditresults"] = {"pass": "{}{}/auditresults/{}?auditResult=pass".format(g.config_items["v2api"]["preroot"],
                                                                                                            g.config_items["v2api"]["root"],
                                                                                                            requested_audit["audit_id"]),
                                                     "fail": "{}{}/auditresults/{}?auditResult=fail".format(g.config_items["v2api"]["preroot"],
                                                                                                            g.config_items["v2api"]["root"],
                                                                                                            requested_audit["audit_id"]),
                                                     "exempt": "{}{}/auditresults/{}?auditResult=notafflicted".format(g.config_items["v2api"]["preroot"],
                                                                                                                      g.config_items[
                                                                                                                          "v2api"]["root"],
                                                                                                                      requested_audit["audit_id"])
                                                     }

    this_results["relationships"]["auditinfo_buckets"] = "{}{}/auditinfo/{}/buckets".format(g.config_items["v2api"]["preroot"],
                                                                                            g.config_items["v2api"]["root"],
                                                                                            args["audit_id"])

    request_data.append(this_results)

    if len(request_data) <= 0:
        g.logger.warning("No Audit Of this Name Found")
        abort(404)

    return_data = {"meta": meta_info,
                   "links": links_info,
                   "data": request_data}

    return jsonify(**return_data)
