#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/sapi/modify endpoint. Designed to initiate a sapi API user.

```swagger-yaml
/custdashboard/modify/{dash_id}/ :
  get:
    description: |
      Modifies a custom audit by either adding, removing or setting an audit_id
      or list of audit_ids
    responses:
      200:
        description: OK
    tags:
      - dashboard
    parameters:
      - name: dash_id
        in: path
        description: |
          Dashboard ID of the dashboard you wish to modify
        schema:
          type: string
        required: true
      - name: modifyorder
        in: query
        description: |
          A dict that tells the system what it should do. Contains one or two keys,
          "add" with an audit_id or list of audit_id's to be added and/or "remove"
          with an audit_id or list of audit_ids to be removed. This is a parsed
          by ast.literal_eval.
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
import requests

custdashboard_modify = Blueprint('api2_custdashboard_modify', __name__)


@custdashboard_modify.route("/custdashboard/modify", methods=['GET', 'POST'])
@custdashboard_modify.route("/custdashboard/modify/", methods=['GET', 'POST'])
@custdashboard_modify.route("/custdashboard/modify/<int:dash_id>", methods=['GET', 'POST'])
@custdashboard_modify.route("/custdashboard/modify/<int:dash_id>/", methods=['GET', 'POST'])
def api2_custdashboard_create(dash_id=None, modifyorder=None):

    meta_dict = dict()
    request_data = dict()
    links_dict = dict()
    error_dict = dict()

    do_query = True
    argument_error = False
    api_error = False
    where_clauses = list()

    do_remove = False
    do_add = False

    remove_ids = list()
    add_ids = list()

    username = g.USERNAME

    # Grab Audits and CustomDashboards From API to help validate.
    audit_list_endpoint = g.HTTPENDPOINT + "/v2/auditlist/"
    custdash_list_endpoint = g.HTTPENDPOINT + "/v2/custdashboard/list/"

    valid_custdash_ids = list()
    valid_audit_ids = list()

    try:
        audit_list_content = requests.get(audit_list_endpoint).content
        custdash_list_content = requests.get(custdash_list_endpoint).content
    except Exception as e:
        error_dict["Error Getting Endpoint"] = "Error getting endpoint: " + \
            str(e)
        api_error = True
    else:
        try:
            audit_list_content_string = audit_list_content.decode("utf-8")
            custdash_list_content_string = custdash_list_content.decode(
                "utf-8")
            audit_list_content_object = json.loads(audit_list_content_string)
            custdash_list_content_object = json.loads(
                custdash_list_content_string)
        except Exception as e:
            api_error = True
            error_dict["api_read_error"] = "Trouble reading data from endpoints. " + \
                str(e)
        else:
            # Let's generate lists validation lists
            valid_audit_ids = [id["attributes"]["audit_id"]
                               for id in audit_list_content_object["data"]]
            valid_custdash_ids = [id["attributes"]["custdashboardid"]
                                  for id in custdash_list_content_object["data"]]

    if "dash_id" in request.args:
        try:
            dash_id = ast.literal_eval(request.args["dash_id"])
        except Exception as e:
            argument_error = True
            error_dict["dash_id_parse_fail"] = "Failed to Parse Dash_id"

    if type(dash_id) is int and dash_id in valid_custdash_ids and api_error == False:
        # Valid dashboard id
        pass
    else:
        argument_error = True
        error_dict["dash_id_incorrect"] = "Either not a valid dash_id or not an integer"

    if "modifyorder" not in request.args:
        argument_error = True
        error_dict["arg_error"] = "Need an order to modify with."
    else:
        try:
            modifyorder = ast.literal_eval(request.args["modifyorder"])
        except Exception as e:
            argument_error = True
            error_dict["modify_order_parse_fail"] = "Unabel to Parse Modify Order, it \
                            ast.literal_eval parsable?"
        else:
            if type(modifyorder) is not dict:
                argument_error = True
                error_dict["modify_order_bad_type"] = "Modify Order not parsed as \
                        dict"
            else:
                # Now testkeys
                if "add" in modifyorder.keys() or "remove" in modifyorder.keys():
                    # Have at least one "proper" order
                    if "add" in modifyorder.keys():
                        # Do add stuff
                        if type(modifyorder["add"]) is list:
                            possible_id_list = [id for id in modifyorder["add"] if type(
                                id) is int and id > 0 and id in valid_audit_ids]
                            if len(possible_id_list) > 0:
                                # There are IDs
                                do_add = True
                                add_ids.extend(possible_id_list)
                        if type(modifyorder["add"]) is int:
                            if modifyorder["add"] > 0 and modifyorder["add"] in valid_audit_ids:
                                do_add = True
                                add_ids.extend(modifyorder["add"])
                    if "remove" in modifyorder.keys():
                        if type(modifyorder["remove"]) is list:
                            possible_id_list = [id for id in modifyorder["remove"] if type(
                                id) is int and id > 0 and id in valid_audit_ids]
                            if len(possible_id_list) > 0:
                                # There are IDs
                                do_remove = True
                                remove_ids.extend(possible_id_list)
                        elif type(modifyorder["remove"]) is int:
                            if modifyorder["remove"] > 0 and modifyorder["remove"] in valid_audit_ids:
                                do_remove = True
                                remove_ids.add(modifyorder["remove"])

                    if do_remove == False and do_add == False:
                        # None Came out right
                        argument_error = True
                        error_dict["incorrect_modify_order"] = "No modifies were accepted."
                else:
                    # Order keys not given
                    argument_error = True
                    error_dict["order_dictionary_incorrect"] = True

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 Custdashboard Create "
    meta_dict["status"] = "In Progress"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/sapi"

    requesttype = "custdashboard_modify"

    remove_query = "delete from custdashboardmembers where fk_custdashboardid = %s and fk_audits_id = %s "
    add_query = "replace into custdashboardmembers ( fk_custdashboardid, fk_audits_id ) VALUES ( %s , %s ) "

    thathappened = dict()
    if do_query and argument_error == False and api_error == False:
        dash_modified = False
        if do_add == True:
            # Add all the items
            thathappened["added"] = list()
            for add_id in add_ids:
                # I wan to Add this Id
                this_arg_list = [dash_id, add_id]
                g.cur.execute(add_query, this_arg_list)
                id_added = g.cur.lastrowid
                thathappened["added"].append(id_added)
                dash_modified = True

        if do_remove == True:
            thathappened["removed"] = remove_ids
            for remove_id in remove_ids:
                # I want to Remove these IDs
                this_arg_list = [dash_id, remove_id]
                g.cur.execute(remove_query, this_arg_list)
                dash_modified = True

        request_data["dash_id"] = dash_id

    else:
        dash_modified = False

    if dash_modified == True:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = thathappened
        response_dict["links"] = links_dict

        return jsonify(**response_dict)

    else:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
