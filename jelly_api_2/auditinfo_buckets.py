#!/usr/bin/env python3

'''
Copyright 2018, VDMS
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

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import time
from configparser import ConfigParser


auditinfo_buckets = Blueprint('api2_auditinfo_buckets', __name__)

@auditinfo_buckets.route("/auditinfo/<int:audit_id>/buckets", methods=['GET'])
@auditinfo_buckets.route("/auditinfo/<int:audit_id>/buckets/", methods=['GET'])
def api2_auditinfo_buckets(audit_id=0):

    if "audit_id" in request.args :
        try:
            audit_id = ast.literal_eval(request.args["audit_id"])
        except Exception as e :
            error_dict["literal_check"] = "Failed with " + str(e)

    requesttime=time.time()

    requesttype = "Audit Buckets"

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "Audit Bucket Information."
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()

    links_info = dict()

    links_info["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditinfo/" + str(audit_id) + "/buckets"
    links_info["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditinfo"
    links_info["children"] = dict()

    request_data = list()

    error_dict = dict()
    do_query = True

    select_query='''select filename from audits where audit_id = %s order by
                    audit_priority desc, audit_id desc '''

    if audit_id > 0 :
        do_query=True
    else:
        do_query=False

    # Select Query
    if do_query :
        g.cur.execute(select_query, audit_id)
        requested_audit = g.cur.fetchone()
        collections_good = True
    else :
        error_dict["do_query"] = "Query Ignored"
        collections_good = False

    #print(requested_audit)

    #Object for parsed audit
    audit = dict()
    audit["id"] = audit_id
    audit["type"] = requesttype
    audit["relationships"] = dict()
    audit["relationships"]["auditinfo"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditinfo/" + str(audit_id)
    audit["attributes"] = dict()

    try:
        # Try to Parse

        # Config Defaults
        this_time=int(time.time())
        back_week=this_time-604800
        back_month=this_time-2628000
        back_quarter=this_time-7844000
        back_year=this_time-31540000
        back_3_year=this_time-94610000
        time_defaults={ "now" : str(this_time), "weekago" : str(back_week), "monthago" : str(back_month), "quarterago" : str(back_quarter), "yearago" : str(back_year), "threeyearago" : str(back_3_year) }

        this_audit_config = ConfigParser(time_defaults)
        this_audit_config.read(requested_audit["filename"])
    except Exception as e:
        # Error if Parse
        error_dict["Parsing Audit"] = "File " + str(requested_audit["filename"]) + " not paresed because of " + format(e)
        collection_good = False
    else:
        for section in this_audit_config :
            if section not in ["GLOBAL", "DEFAULT"] :
                for item in this_audit_config[section]:
                    if item in ["filters", "comparisons" ] :
                        onelinethisstuff = "".join(this_audit_config[section][item].splitlines())
                        #print(onelinethisstuff)
                        try:
                            audit["attributes"][item] = ast.literal_eval(onelinethisstuff)
                        except Exception as e:
                            print("Verification Failed. Use verifyAudits.py for more details")
                            collection_good=False
        request_data.append(audit)

    if collections_good :
        return jsonify(meta=meta_info, data=request_data, links=links_info)
    else :
        return jsonify(meta=meta_info, errors=error_dict, links=links_info)
