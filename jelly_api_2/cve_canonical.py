#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/cve/ubuntu/{cve_name}/ :
  get:
    description: |
      Gives you all the pops that Jellyfish has recently seen.
    responses:
      200:
        description: OK
    tags:
      - cve
    parameters:
      - name: cve_name
        in: path
        description: |
            The CVE you wish to recieve data against
        schema:
          type: string
        required: true
        format: cve
        pattern: ^[Cc][Vv][Ee]-\d{4}-\d{4,9}$
```
"""

import json
import ast
import time
import hashlib
import os

from flask import current_app, Blueprint, g, request, jsonify, abort

import audittools
import manoward

cve_canonical = Blueprint('api2_cve_canonical', __name__)


@cve_canonical.route("/cve/canonical", methods=['GET'])
@cve_canonical.route("/cve/canonical/", methods=['GET'])
@cve_canonical.route("/cve/canonical/<string:cve_name>", methods=['GET'])
@cve_canonical.route("/cve/canonical/<string:cve_name>/", methods=['GET'])
@cve_canonical.route("/cve/ubuntu/<string:cve_name>", methods=['GET'])
@cve_canonical.route("/cve/ubuntu/<string:cve_name>/", methods=['GET'])
def api2_cve_canonical(cve_name=None):
    '''
    Returns Data about an Ubuntu CVE
    '''

    args_def = {"cve_name": {"req_type": str,
                             "default": cve_name,
                             "required": True,
                             "sql_param": False,
                             "qdeparse": False,
                             "regex_val": r"^[Cc][Vv][Ee]-\d{4}-\d{4,9}$"}}

    args = manoward.process_args(args_def,
                                 request.args)

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Canonical CVE Information for Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()
    #meta_info["global_usn_cache"] = "{}/cve_canonical.json".format(g.config_items["v2api"]["cachelocation"])
    #meta_info["global_usn_drift_tolerance"] = g.config_items["v2api"].get("usn_drift", 3600)

    argument_error = False

    requesttime = time.time()

    requesttype = "canonical_cve"

    links_info = dict()

    links_info["self"] = "{}{}/cve/canonical/{}".format(g.config_items["v2api"]["preroot"],
                                                        g.config_items["v2api"]["root"],
                                                        args["cve_name"])

    links_info["parent"] = "{}{}/cve".format(g.config_items["v2api"]["preroot"],
                                             g.config_items["v2api"]["root"])

    links_info["children"] = dict()

    request_data = list()

    try:
        g.logger.debug("Requesting Data for CVE : {}".format(args["cve_name"]))
        this_cve_obj = audittools.mowCVEUbuntu(cve=args["cve_name"])

    except Exception as get_cve_error:
        g.logger.error("Unable to Pull CVE : {}".format(args["cve_name"]))
        g.logger.debug("Error : {}".format(get_cve_error))
        abort(500)
    else:
        this_cve_data = this_cve_obj.summarize()

    return jsonify(meta=meta_info, data=this_cve_data, links=links_info)
