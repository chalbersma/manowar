#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/sapi/adduser endpoint. Designed to initiate a sapi API user.

```swagger-yaml
/sapi/adduser/ :
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
        x-astliteraleval: true
        in: query
        description: |
          Username that wants to be created.
        schema:
          type: string
        required: true
      - name: purpose
        x-astliteraleval: true
        in: query
        description: |
          Reason that user was created. Requires a ticket denoted in brackets.
        schema:
          type: string
        required: true
```

'''

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory
import json
import ast
import time
import os
import hashlib
import re
import manoward

sapi_adduser = Blueprint('api2_sapi_adduser', __name__)


@sapi_adduser.route("/sapi/adduser", methods=['GET'])
@sapi_adduser.route("/sapi/adduser/", methods=['GET'])
def api2_sapi_adduser(username=None, purpose=None):

    meta_dict = dict()
    request_data = dict()
    links_dict = dict()
    error_dict = dict()

    #
    # Don't allow local whitelist and api users to add users.
    # Require an ldap user to create a new dashboard.
    #

    this_endpoint_restrictions = (
        ("conntype", "whitelist"), ("conntype", "robot"))
    this_endpoint_endorsements = (("conntype", "ldap"), )

    manoward.process_endorsements(endorsements=this_endpoint_endorsements,
                                  restrictions=this_endpoint_restrictions,
                                  session_endorsements=g.session_endorsements,
                                  session_restrictions=g.session_restrictions,
                                  do_abort=True)

    do_query = True
    argument_error = False
    where_clauses = list()

    find_ticket_regex = "\[[\w|-]+\]"

    if "username" in request.args:
        username = ast.literal_eval(request.args["username"])

    if "purpose" in request.args:
        purpose = ast.literal_eval(request.args["purpose"])
        if re.search(find_ticket_regex, purpose) == None:
            # No ticket found
            argument_error = True
            error_dict["purpose_error"] = "No ticket denotation found."
            purpose = None

    if username is None or purpose is None:
        argument_error = True
        do_query = False

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 SAPI Add User "
    meta_dict["status"] = "In Progress"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/sapi"

    requesttype = "sapi_adduser"

    find_existing_user_args = [username]
    find_existing_user_query = "select apiuid, apiusername, apiuser_purpose from apiUsers where apiusername = %s "

    if do_query and argument_error == False:
        g.cur.execute(find_existing_user_query, find_existing_user_args)
        users = g.cur.fetchall()
        amount_of_users = len(users)
        if amount_of_users == 0:
            do_insert = True
        else:
            error_dict["user_exists"] = "User " + \
                str(username) + " already has user."
            do_insert = False
    else:
        error_dict["do_query"] = "Query Ignored"
        do_insert = False

    if do_insert:
        # No Users Found
        add_new_user_args = [username, purpose]
        add_new_user_query = "insert into apiUsers (apiusername, apiuser_purpose) VALUES ( %s , %s) "

        # In the Future add Ticket Integration via ecbot (or ecbot like system) here.
        g.cur.execute(add_new_user_query, add_new_user_args)

        user_id = g.cur.lastrowid
        user_added = True
        request_data["userid"] = user_id
        request_data["insert_successful"] = True

    else:
        user_added = False

    if user_added == True:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = request_data
        response_dict["links"] = links_dict

        return jsonify(**response_dict)

    else:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
