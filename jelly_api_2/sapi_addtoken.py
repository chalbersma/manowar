#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/sapi/adduser endpoint. Designed to initiate a sapi API user.

```swagger-yaml
/sapi/addtoken/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Adds a new token for a particular user.
    responses:
      200:
        description: OK
    tags:
      - auth
    parameters:
      - name: user
        x-astliteraleval: true
        in: query
        description: |
          Username or UserID of user who should have token created.
        schema:
          type: string
        required: true
      - name: validfor
        x-astliteraleval: true
        in: query
        description: |
          How many days token should be valid for (default 7 days)
        schema:
          type: string
        required: false
      - name: tokentype
        x-astliteraleval: true
        in: query
        description: |
          What type of token to insert. Default is sapi.
        schema:
          type: string
        required: false
```

'''

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory
import json
import ast
import time
import os
import hashlib
import re
import uuid
#import secrets
import string
import random

import manoward

sapi_addtoken = Blueprint('api2_sapi_addtoken', __name__)


@sapi_addtoken.route("/sapi/addtoken", methods=['GET'])
@sapi_addtoken.route("/sapi/addtoken/", methods=['GET'])
def api2_sapi_addtoken(user=None, validfor=7, tokentype="sapi"):

    meta_dict = dict()
    request_data = dict()
    links_dict = dict()
    error_dict = dict()

    #
    # Don't allow local whitelist and api users to create tokens.
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

    if "user" in request.args:
        user = ast.literal_eval(request.args["user"])
        if type(user) is str:
            username = user
            use_username = True
            use_uid = False
        elif type(user) is int:
            userid = user
            use_username = False
            use_uid = True
        else:
            error_dict["bad_user"] = "Unable to properly parse user."
            argument_error = True

    if "validfor" in request.args:
        validfor = ast.literal_eval(request.args["validfor"])
        if type(validfor) is int and validfor < 90 and validfor > 0:
            # validfor Okay allow override
            pass
        else:
            argument_error = True
            error_dict["bad_valid"] = "Bad valid date, either not int or int >=90 days"
    else:
        validfor = 7

    if "tokentype" in request.args:
        tokentype = ast.literal_eval(request.args["tokentype"])
        if type(tokentype) is str and len(tokentype) > 0 and tokentype in g.config_items["tokenmgmt"]["vt_types"]:
            # Token type is okay
            pass
        else:
            argument_error = True
            # nosec
            error_dict["bad_token_type"] = "Bad token type, either zero lenght, not a string or not in the validated list"

    if argument_error:
        do_query = False

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 SAPI Add Token "
    meta_dict["status"] = "In Progress"

    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/sapi"

    requesttype = "sapi_addtoken"

    if use_username:
        query_tail = "apiusername = %s"
        find_existing_user_args = [username]
    elif use_uid:
        query_tail = "apiuid = %s"
        find_existing_user_args = [userid]

    # The query is paramaterized. See Lines 101 through 106 for proof.
    find_existing_user_query = "select apiuid from apiUsers where  " + query_tail  # nosec

    if do_query:
        g.cur.execute(find_existing_user_query, find_existing_user_args)
        user = g.cur.fetchone()
        amount_of_users = g.cur.rowcount
        if amount_of_users == 1:
            # Verified User Exists
            retrieved_uid = user["apiuid"]
            do_insert = True
        else:
            error_dict["user_not_found"] = "User has not been found in database."
            do_insert = False
    else:
        error_dict["do_query"] = "Query Ignored"
        do_insert = False

    if do_insert:
        # User Found

        # Generate Key
        key_value = str(uuid.uuid4())

        # Generate Salt
        # When we migrate to python3.6+ we can upgrade to the secrets library
        salt_value = random.randint(0, 4294967294)  # nosec
        #salt_library = string.digits
        # Secrets not available until python3.6
        #salt_value = ''.joint(choice(alhpabet) for i in range(9))

        # No Users Found
        new_token_args = [tokentype, salt_value,
                          key_value, retrieved_uid, validfor, salt_value]
        new_token_query = '''insert into apiActiveTokens
            (tokentype, token, fk_apikeyid, token_expire_date, salt)
            VALUES( %s, SHA2(CONCAT(%s,%s),512) , %s, (NOW() + INTERVAL %s DAY), %s ) '''  # nosec

        # In the Future add Ticket Integration via ecbot (or ecbot like system) here.
        g.cur.execute(new_token_query, new_token_args)

        user_id = g.cur.lastrowid
        user_added = True
        token_data = dict()
        request_data["userid"] = retrieved_uid
        request_data["new_key"] = key_value
        request_data["validfor_days"] = validfor
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
