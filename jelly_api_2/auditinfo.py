#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.


```swagger-yaml
/auditinfo/{audit_id}/ :
  get:
    description: |
      Get's the stored information about a given audit. Does not include the Bucket or Match Logic
      as there is currently a bug about those items.
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

'''

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import time


auditinfo = Blueprint('api2_auditinfo', __name__)

@auditinfo.route("/auditinfo", methods=['GET'])
@auditinfo.route("/auditinfo/", methods=['GET'])
@auditinfo.route("/auditinfo/<int:audit_id>", methods=['GET'])
@auditinfo.route("/auditinfo/<int:audit_id>/", methods=['GET'])
def api2_auditinfo(audit_id=0):

    if "audit_id" in request.args :
        try:
            audit_id = ast.literal_eval(request.args["audit_id"])
        except Exception as e :
            error_dict["literal_check"] = "Failed with " + str(e)

    requesttime=time.time()

    requesttype = "Audit Details"

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Audit Information Endpoint for Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()

    links_info = dict()

    links_info["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditinfo"
    links_info["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/"
    links_info["children"] = dict()
    links_info["children"]["Audit Buckets"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditinfo/${audit_id}/buckets"

    request_data = list()

    error_dict = dict()
    do_query = True

    select_query='''select audit_id, audit_name, audit_priority, \
                            audit_short_description, audit_long_description,
                            audit_primary_link, \
                            COLUMN_JSON(audit_secondary_links) as 'audit_secondary_links' \
                            from audits
                            where audit_id = %s
                            order by audit_priority desc, audit_id desc ;'''

    if audit_id > 0 :
        # It's Okay the Item is an Int & it's a positive number (as my IDs are all unsigned)
        do_query=True
    else:
        do_query=False

    ## Build Query
    # Debug
    #print(select_query)

    # Select Query
    if do_query :
        g.cur.execute(select_query, audit_id)
        requested_audit = g.cur.fetchone()
        collections_good = True
    else :
        error_dict["do_query"] = "Query Ignored"
        collections_good = False

    # Clean Secondary Links
    if collections_good :
        try:

            this_secondary_link = ast.literal_eval(requested_audit["audit_secondary_links"])
            #print(this_secondary_link)
            #print(type(this_secondary_link))

        except Exception as e:
            error_dict["Error Reading Secondary Links"] = "Error Reading Secondary Links" + str(e)
            collections_good = False
        else :
            requested_audit["audit_secondary_links"] = this_secondary_link


    if collections_good :
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = requested_audit["audit_id"]
        this_results["attributes"] = requested_audit
        this_results["relationships"] = dict()
        this_results["relationships"]["auditresults"] = { "pass" : g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditresults/" + str(requested_audit["audit_id"]) + "?auditResult='pass'",
                                                            "fail" : g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditresults/" + str(requested_audit["audit_id"]) + "?auditResult='fail'",
                                                            "exempt" : g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditresults/" + str(requested_audit["audit_id"]) + "?auditResult='notafflicted'" }
        this_results["relationships"]["display_auditresults"] = { "pass" : g.config_items["v2ui"]["preroot"] + g.config_items["v2ui"]["root"] + "/auditresults/" + str(requested_audit["audit_id"]) + "?auditResult='pass'",
                                                            "fail" : g.config_items["v2ui"]["preroot"] + g.config_items["v2ui"]["root"] + "/auditresults/" + str(requested_audit["audit_id"]) + "?auditResult='fail'",
                                                            "exempt" : g.config_items["v2ui"]["preroot"] + g.config_items["v2ui"]["root"] + "/auditresults/" + str(requested_audit["audit_id"]) + "?auditResult='notafflicted'" }
        this_results["relationships"]["auditinfo_buckets"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditinfo/" + str(requested_audit["audit_id"]) + "/buckets"

        request_data.append(this_results)
    else :
        error_dict["ERROR"] = ["No Collections"]
        collections_good = False

    #print(request_data)

    if collections_good :
        return jsonify(meta=meta_info, data=request_data, links=links_info)
    else :
        return jsonify(meta=meta_info, errors=error_dict, links=links_info)


