#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

gpg_preauth/

You will post a json to this endpoint that has a gpg (ascii) signed message
that has a timestamp that is +-5 minutes from now (Effectively `echo $(date +%s) | gpg2 -s -a`)

```swagger-yaml
/sapi/gpg_preauth/ :
  get:
    produces:
      - application/json
    description: |
      Send me a json does stuff that I'm still deciding.
    responses:
      200:
        description: OK
    parameters:
      - name: username
        in: path
        description: |
          The id or username of your user.
        type: integer
        required: true
      - name: username
        in: path
        description: |
          The id or username of your user.
        type: integer
        required: true
```

'''

from flask import current_app, Blueprint, g, request, jsonify

import json
import pprint
import gnupg
import ast

preauth = Blueprint('preauth', __name__)

@preauth.route("/preauth", methods=['GET','POST'])
@preauth.route("/preauth/", methods=['GET','POST'])
def gpg_preauth():

    error_dict = dict()
    response_dict = dict()

    error=False
    where_clause = " "

    given_data = request.json

    print(given_data["signed_message"])


    if "username" in request.args :
        try:
            print(request.args["username"])
            username = ast.literal_eval('"' + request.args["username"] + '"')
        except Exception as e :
            error_dict["literal_check"] = "Failed with " + str(e)
            error=True
        else:
            if type(username) == str:
                pass
            else:
                error=True
                error_dict["username_type_check"] = "Username not a string"
            if username.isalpha() :
                # Okay username is all alphanumeric characters
                pass
            else:
                error=True
                error_dict["username_value_check"] = "Username is blank or has non alphanumeric characters"

    try:
        username
    except NameError as e:
        error=True
        error_dict["paramater_error"] = "No Username Given" + str(e)
    else:
        pass


    # Get Username keyid


    if error != True :
        keyid_query_args = [ str(username) ]
        keyid_query = "select sapiuid, sapikeyid, sapiusername from sapiUsers where sapiusername = %s "

        g.cur.execute(keyid_query, keyid_query_args)
        user_information = g.cur.fetchone()
        user_query_good = True
        print(user_information)

    else :
        error_dict["do_query"] = "Query Ignored"
        user_query_good = False

    # Create GPG Object
    gpg_object = gnupg.GPG(homedir=g.AUTHCONFIG["gpg_home"])

    active_keys = gpg_object.list_keys()

    decrypted_data = gpg_object.decrypt(given_data["signed_message"])
    verified = gpg_object.verify(given_data["signed_message"])

    '''
    print(type(decrypted_data.data))
    print(decrypted_data.data)
    print(type(decrypted_data.ok))
    print(decrypted_data.ok)
    print(type(decrypted_data.status))
    print(decrypted_data.status)
    print(type(decrypted_data.username))
    print(decrypted_data.username)
    print(type(verified))
    print(verified)
    print(verified.status)
    print(verified.valid)
    print(verified.fingerprint)
    print(verified.pubkey_fingerprint)
    '''



    if error:
        return jsonify(error=error_dict)
    else :
        return jsonify(data=response_dict)
