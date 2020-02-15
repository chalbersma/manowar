#!/usr/bin/env python3

"""
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/sapi/adduser endpoint. Designed to initiate a sapi API user.

```swagger-yaml
/adduser/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Designed to grab a list of hosts that either pass or fail an audit
      along with the relevant data about each host. Similar to the audit_table
      item from the old api.
    responses:
      200:
        description: OK
    tags:
      - auth
    parameters:
      - name: username
        in: query
        description: |
          Username that wants to be created. Must be Lowercase and  All Letters
        schema:
          type: string
        required: true
      - name: purpose
        in: query
        description: |
          Reason that user was created. Requires a ticket denoted in brackets. Like [TKT-101]
        schema:
          type: string
        required: true
```

"""

from flask import Blueprint, g, request, jsonify, abort

import manoward

sapi_adduser = Blueprint('api2_sapi_adduser', __name__)


@sapi_adduser.route("/adduser", methods=['GET'])
@sapi_adduser.route("/adduser/", methods=['GET'])
@sapi_adduser.route("/sapi/adduser", methods=['GET'])
@sapi_adduser.route("/sapi/adduser/", methods=['GET'])
def api2_sapi_adduser():

    """
    An endpoint that let's you add a API Username/Purpose Combination
    """

    this_endpoint_restrictions = (("conntype", "whitelist"), ("conntype", "robot"))

    this_endpoint_endorsements = (("conntype", "ldap"), )

    manoward.process_endorsements(endorsements=this_endpoint_endorsements,
                                  restrictions=this_endpoint_restrictions,
                                  session_endorsements=g.session_endorsements,
                                  session_restrictions=g.session_restrictions,
                                  ignore_abort=g.debug)

    args_def = {"purpose": {"req_type": str,
                            "default": None,
                            "required": True,
                            "qdeparse": True,
                            "regex_val": r"\[[\w|-]+\]"},
                "username" : {"req_type": str,
                              "default": None,
                              "required": True,
                              "require_alpha" : True,
                              "require_lower" : True,
                              "qdeparse" : True}}

    args = manoward.process_args(args_def,
                                 request.args)

    meta_dict = dict()
    request_data = dict()
    links_dict = dict()
    error_dict = dict()

    do_query = True
    argument_error = False

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 SAPI Add User "
    meta_dict["status"] = "In Progress"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/adduser?{}".format(g.config_items["v2api"]["preroot"],
                                                  g.config_items["v2api"]["root"],
                                                  args["qdeparse_string"])
    requesttype = "sapi_adduser"

    find_existing_user_args = [args["username"]]
    find_existing_user_query = "select count(*) from apiUsers where apiusername = %s "

    fence = manoward.run_query(g.cur,
                               find_existing_user_query,
                               args=find_existing_user_args,
                               one=True,
                               do_abort=True,
                               require_results=True)

    if fence["count"] >= 1:
        g.logger.error("Duplicate Person Specified, Ignoring This Request")
        error_dict["user_exists"] = "User {} already Exists".format(args["username"])

        return jsonify(meta=meta_dict, links=links_dict, error=error_dict)


    add_new_user_args = [args["username"], args["purpose"], args["purpose"]]
    add_new_user_query = "insert into apiUsers (apiusername, apiuser_purpose) VALUES ( %s , %s)"


    try:
        # In the Future add Ticket Integration via ecbot (or ecbot like system) here.
        g.cur.execute(add_new_user_query, add_new_user_args)

        user_id = g.cur.lastrowid
    except Exception as insert_error:
        g.logger.error("Unable to Insert User {} into Database".format(args["username"]))
        error_dict["Error"] = "Error on Insert"
        error_dict["specific"] = str(insert_error)

        return jsonify(meta=meta_dict, links=links_dict, error=error_dict)
    else:
        request_data["userid"] = user_id
        request_data["insert_successful"] = True
        request_data["relationships"] = dict()
        request_data["relationships"]["user"] = "{}{}/listusers?apiuid={}".format(g.config_items["v2api"]["preroot"],
                                                                                  g.config_items["v2api"]["root"],
                                                                                  user_id)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
