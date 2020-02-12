#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/dashboard/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Get the Dashboard information about.
    responses:
      200:
        description: OK
    tags:
      - dashboard
    parameters:
      - name: pass_audits
        in: query
        description: | 
          Specifying this variable means you only want the passing audits 
          (audits with zero failures).
          Note that specifying this option simultaneously with fail_audits
          will lead to a warning but will return all audits.
        schema:
          type: string
        enum: [true, false]
      - name: fail_audits
        in: query
        description: | 
          Specifying this variable means you only want the failing audits 
          (audits with zero failures).
          Note that specifying this option simultaneously with pass_audits
          will lead to a warning but will return all audits.
        schema:
          type: string
        enum: [true, false]
      - name: cust_dash_id
        in: query
        description: |
          Only Return audits in this custom dashboard (referenced by ID).
        schema:
          type: integer

```
"""

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import time

import manoward


dashboard = Blueprint('api2_dashboard', __name__)


@dashboard.route("/dashboard", methods=['GET'])
@dashboard.route("/dashboard/<int:cust_dash_id>/", methods=['GET'])
def api2_dashboard(cust_dash_id=None):

    args_def = {"pass_audits": {"required": True,
                                "default": "false",
                                "req_type": str,
                                "enum": ["true", "false"]},
                "fail_audits": {"required": True,
                                "default": "false",
                                "req_type": str,
                                "enum": ["true", "false"]},
                "cust_dash_id": {"required": False,
                                 "default": cust_dash_id,
                                 "req_type": int,
                                 "positive": True}
                }

    args = manoward.process_args(args_def, request.args)

    requesttime = time.time()

    requesttype = "dashboard_query"

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Dashboard Query for Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()

    links_info = dict()

    links_info["self"] = "{}{}/dashboard".format(g.config_items["v2api"]["preroot"],
                                                 g.config_items["v2api"]["root"])

    links_info["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_info["children"] = dict()

    request_data = list()

    error_dict = dict()
    do_query = True

    dashboard_query_head = '''
SELECT audits.audit_name,
       audits.audit_id,
       audits.audit_priority,
       audit_short_description,
       audits_by_acoll.acoll_passed,
       audits_by_acoll.acoll_failed,
       audits_by_acoll.acoll_exempt
FROM
  (SELECT fk_audits_id,
          max(acoll_last_audit) AS maxtime
   FROM audits_by_acoll
   WHERE acoll_last_audit >= FROM_UNIXTIME(%s)
   GROUP BY fk_audits_id) AS maxdate
JOIN audits_by_acoll ON audits_by_acoll.acoll_last_audit = maxtime
AND audits_by_acoll.fk_audits_id = maxdate.fk_audits_id
JOIN audits ON audits.audit_id = maxdate.fk_audits_id
'''

    dashboard_query_args = [str(g.twoDayTimestamp)]

    # Inject Custom Dashboard Items
    # print(cust_dash_id)
    if args["cust_dash_id"] is not None:
        custdashboard_join = '''
        JOIN
          (SELECT fk_audits_id AS dash_audit_id
          FROM custdashboardmembers
          WHERE fk_custdashboardid = %s ) AS thisdash ON maxdate.fk_audits_id = thisdash.dash_audit_id
        '''

        dashboard_query_args.append(args["cust_dash_id"])
        dashboard_query_head = dashboard_query_head + custdashboard_join

        meta_info["cust_dash_id"] = args["cust_dash_id"]
        meta_info["custom_dashbaord"] = True

        this_endpoint = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + \
            "/custdashboard/list/{}/".format(args["cust_dash_id"])
        links_info["cust_dash_id"] = this_endpoint

    else:
        meta_info["custom_dashboard"] = False

    if (args["pass_audits"] == "false" and args["fail_audits"] == "false") or (args["pass_audits"] == "true" and args["pass_audits"] == "true"):
        # Give me Everything
        dashboard_query_mid = "  "
    elif args["pass_audits"] == "true":
        # I want only the Audits that have completely passed (Where there are no failures)
        dashboard_query_mid = " where acoll_failed = 0 "
        meta_info["Query Info"] = "Only Passing Audits have been returned (Audits where there are zero failures)."
    elif args["fail_audits"] == "true":
        # I want only the Audits that have failed (Where there are at least one failure)
        dashboard_query_mid = " where acoll_failed > 0 "
        meta_info["Query Info"] = "Only Failing Audits have been returnd (Audits where there are more than zero failures)."

    dashboard_query_tail = "order by audits.audit_priority desc, acoll_failed desc"

    dashboard_query = dashboard_query_head + \
        dashboard_query_mid + dashboard_query_tail

    # Select Query
    if do_query is True:

        results = manoward.run_query(g.cur,
                                     dashboard_query,
                                     args=dashboard_query_args,
                                     one=False,
                                     do_abort=True,
                                     require_results=False)

        all_collections = results["data"]
        amount_of_collections = len(results["data"])

    else:
        error_dict["do_query"] = "Query Ignored"
        amount_of_collections = 0

    if amount_of_collections > 0:
        collections_good = True
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_collections)):
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = all_collections[i]["audit_id"]
            this_results["attributes"] = all_collections[i]
            this_results["attributes"]["total_servers"] = all_collections[i]["acoll_exempt"] + \
                all_collections[i]["acoll_failed"] + \
                all_collections[i]["acoll_passed"]
            this_results["attributes"]["total_pass_fail"] = all_collections[i]["acoll_failed"] + \
                all_collections[i]["acoll_passed"]

            this_results["attributes"]["pass_percent"] = all_collections[i]["acoll_passed"] / \
                this_results["attributes"]["total_servers"]
            this_results["attributes"]["pass_percent_int"] = int(
                (all_collections[i]["acoll_passed"] / this_results["attributes"]["total_servers"]) * 100)
            this_results["attributes"]["fail_percent"] = all_collections[i]["acoll_failed"] / \
                this_results["attributes"]["total_servers"]
            this_results["attributes"]["fail_percent_int"] = int(
                (all_collections[i]["acoll_failed"] / this_results["attributes"]["total_servers"]) * 100)
            this_results["attributes"]["exempt_percent"] = all_collections[i]["acoll_exempt"] / \
                this_results["attributes"]["total_servers"]
            this_results["attributes"]["exempt_percent_int"] = int(
                (all_collections[i]["acoll_exempt"] / this_results["attributes"]["total_servers"]) * 100)

            this_results["relationships"] = dict()
            this_results["relationships"]["auditinfo"] = g.config_items["v2api"]["preroot"] + \
                g.config_items["v2api"]["root"] + "/auditinfo/" + \
                str(all_collections[i]["audit_id"])
            this_results["relationships"]["display_auditinfo"] = g.config_items["v2ui"]["preroot"] + \
                g.config_items["v2ui"]["root"] + "/auditinfo/" + \
                str(all_collections[i]["audit_id"])
            this_results["relationships"]["auditresults"] = {"pass": g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditresults/" + str(all_collections[i]["audit_id"]) + "?auditResult='pass'",
                                                             "fail": g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditresults/" + str(all_collections[i]["audit_id"]) + "?auditResult='fail'",
                                                             "exempt": g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditresults/" + str(all_collections[i]["audit_id"]) + "?auditResult='notafflicted'"}
            this_results["relationships"]["display_auditresults"] = {"pass": g.config_items["v2ui"]["preroot"] + g.config_items["v2ui"]["root"] + "/auditresults/" + str(all_collections[i]["audit_id"]) + "?auditResult='pass'",
                                                                     "fail": g.config_items["v2ui"]["preroot"] + g.config_items["v2ui"]["root"] + "/auditresults/" + str(all_collections[i]["audit_id"]) + "?auditResult='fail'",
                                                                     "exempt": g.config_items["v2ui"]["preroot"] + g.config_items["v2ui"]["root"] + "/auditresults/" + str(all_collections[i]["audit_id"]) + "?auditResult='notafflicted'"}

            # Now pop this onto request_data
            request_data.append(this_results)
    else:
        error_dict["ERROR"] = ["No Collections"]
        collections_good = False

    all_res = {"meta": meta_info,
               "links": links_info}

    if collections_good:
        all_res["data"] = request_data
    else:
        all_res["errors"] = error_dict

    return jsonify(**all_res)
