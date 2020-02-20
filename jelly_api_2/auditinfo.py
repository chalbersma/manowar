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
from flask import Blueprint, g, request, jsonify, abort

import manoward
import audittools


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

    audit_obj = audittools.AuditSource(do_db=True,
                                       db_cur=g.cur,
                                       audit_id=args["audit_id"])

    meta_info["audit_name"] = audit_obj.audit_name
    meta_info["audit_id"] = audit_obj.audit_id


    this_results = dict()
    this_results["type"] = requesttype
    this_results["id"] = args["audit_id"]
    this_results["attributes"] = audit_obj.return_audit()
    this_results["relationships"] = dict()
    this_results["relationships"]["auditresults"] = {"pass": "{}{}/auditresults/{}?auditResult=pass".format(g.config_items["v2api"]["preroot"],
                                                                                                            g.config_items["v2api"]["root"],
                                                                                                            args["audit_id"]),
                                                     "fail": "{}{}/auditresults/{}?auditResult=fail".format(g.config_items["v2api"]["preroot"],
                                                                                                            g.config_items["v2api"]["root"],
                                                                                                            args["audit_id"]),
                                                     "exempt": "{}{}/auditresults/{}?auditResult=notafflicted".format(g.config_items["v2api"]["preroot"],
                                                                                                                      g.config_items["v2api"]["root"],
                                                                                                                      args["audit_id"])
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
