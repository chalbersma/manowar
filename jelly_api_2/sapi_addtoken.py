#!/usr/bin/env python3

"""
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/sapi/adduser endpoint. Designed to initiate a sapi API user.

```swagger-yaml
/addtoken/ :
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
      - name: apiuid
        in: query
        description: |
          Username or UserID of user who should have token created.
        schema:
          type: integer
        required: true
      - name: validfor
        in: query
        description: |
          How many days token should be valid for (default 7 days)
        schema:
          type: integer
        required: true
        default: 7
      - name: tokentype
        in: query
        description: |
          What type of token to insert. Default is sapi.
        schema:
          type: string
          enum: [robot, storage]
        required: true
        default: storage
```

"""

import uuid
import secrets

from flask import Blueprint, g, request, jsonify, abort

import manoward

sapi_addtoken = Blueprint('api2_sapi_addtoken', __name__)


@sapi_addtoken.route("/addtoken", methods=['GET'])
@sapi_addtoken.route("/addtoken/", methods=['GET'])
@sapi_addtoken.route("/sapi/addtoken", methods=['GET'])
@sapi_addtoken.route("/sapi/addtoken/", methods=['GET'])
def api2_sapi_addtoken(validfor=7, tokentype="sapi"):

    """
    SAPI Add Token
    """

    this_endpoint_restrictions = (
        ("conntype", "whitelist"), ("conntype", "robot"))
    this_endpoint_endorsements = (("conntype", "ldap"), )

    manoward.process_endorsements(endorsements=this_endpoint_endorsements,
                                  restrictions=this_endpoint_restrictions,
                                  session_endorsements=g.session_endorsements,
                                  session_restrictions=g.session_restrictions,
                                  ignore_abort=g.debug)

    args_def = {"apiuid" : {"req_type": int,
                            "default": None,
                            "required": True,
                            "positive" : True,
                            "qdeparse" : True},
                "validfor" : {"req_type" : int,
                              "default" : validfor,
                              "positive" : True,
                              "qdeparse" : True},
                "tokentype" : {"req_type" : str,
                               "default" : tokentype,
                               "qdeparse" : True,
                               "enum" : g.config_items["tokenmgmt"]["token_types"]
                               }
               }

    args = manoward.process_args(args_def,
                                 request.args)
    meta_dict = dict()
    request_data = dict()
    links_dict = dict()
    error_dict = dict()

    argument_error = False

    if args["validfor"] > 90:
        g.logger.error("Refusing to Create Token as Token is more than 90 Days Old")
        g.logger.warning("DENIED: {} Requested a Token for {} of Age {}".format(g.USERNAME,
                                                                              args["apiuser"],
                                                                              args["validfor"]))
        abort(406)

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 SAPI Add Token "
    meta_dict["status"] = "In Progress"

    links_dict["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/addtoken?{}".format(g.config_items["v2api"]["preroot"],
                                                   g.config_items["v2api"]["root"],
                                                   args["qdeparse_string"])

    requesttype = "sapi_addtoken"

    find_existing_user_args = [args["apiuid"]]
    find_existing_user_query = "select count(*) from apiUsers where apiuid=%s"

    fence = manoward.run_query(g.cur,
                               find_existing_user_query,
                               args=find_existing_user_args,
                               one=True,
                               do_abort=True,
                               require_results=True)

    if fence["count"] == 0:
        g.logger.error("Nobody with this Username Exists")
        g.logger.warning("DENIED: {} Requested a Token for {} of Age {}".format(g.USERNAME,
                                                                                args["apiuser"],
                                                                                args["validfor"]))
        error_dict["nobody"] = "Userid {} is Incorrect".format(args["apiuid"])

        return jsonify(meta=meta_dict, links=links_dict, error=error_dict)

    # Generate Key
    key_value = str(uuid.uuid4())

    salt_library = string.digits
    salt_value = ''.join(secrets.choice(salt_library) for i in range(32))

    new_token_args = [args["tokentype"],
                      salt_value, key_value,
                      args["apiuid"],
                      validfor,
                      salt_value]

    # Note that Token doesn't get the token but a
    new_token_query = '''insert into apiActiveTokens
                         (tokentype, token, fk_apikeyid, token_expire_date, salt)
                         VALUES(%s, 
                                SHA2(CONCAT(%s,%s),512), 
                                %s,
                                (NOW() + INTERVAL %s DAY),
                                %s)'''

        # In the Future add Ticket Integration via ecbot (or ecbot like system) here.
    try:
        g.cur.execute(new_token_query, new_token_args)
        token_id = g.cur.lastrowid
    except Exception as Token_Error:
        g.logger.error("Unable to Generate Token")
        g.logger.debug("{}".format(Token_Error))
        abort(500)
    else:
        request_data["userid"] = args["apiuid"]
        request_data["new_key"] = key_value
        request_data["validfor_days"] = args["validfor"]
        request_data["token_id"] = token_id

    return jsonify(meta=meta_dict, links=links_dict, data=request_data)
