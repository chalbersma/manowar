#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/sapi/puthostjson/ :
  post:
    description: |
      Accepts a valid host json and stores it in the api. This call is fenced
      by an api token that you need to specify and won't work in the interactive
      version of this.
    tags:
      - sapi
    responses:
      200:
        description: OK
      401:
        description: Unauthorized (Most likely no Token given)
    requestBody:
      content:
        application/json:
          required: true
          schema:
            type: object
```
"""

from flask import current_app, Blueprint, g, request, jsonify, abort

import manoward
from manoward.storage import storage

puthostjson = Blueprint('puthostjson', __name__)


@puthostjson.route("/puthostjson", methods=['GET', 'POST'])
@puthostjson.route("/puthostjson/", methods=['GET', 'POST'])
@puthostjson.route("/sapi/puthostjson", methods=['GET', 'POST'])
@puthostjson.route("/sapi/puthostjson/", methods=['GET', 'POST'])
def generic_puthostjson():
    '''
    Runs the /puthostjson endpoint. This stores the data sent from manowar_agent
    '''

    meta_dict = dict()
    #request_data = list()
    links_dict = dict()
    error_dict = dict()

    g.logger.warning("Recieved Upload Request.")

    this_endpoint_endorsements = (("conntype", "sapi"),)

    manoward.process_endorsements(endorsements=this_endpoint_endorsements,
                                  session_endorsements=g.session_endorsements,
                                  ignore_abort=g.debug)

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish SAPI PutHostJSON "
    meta_dict["status"] = "In Progress"

    error = False

    g.logger.debug("Recieved Authenticated Request Request")

    if request.json is None:
        error_dict["nodata"] = True
        error = True

    if error is False:

        # Note that this is an API host
        request.json["collection_status"] = "STINGCELL"

        # Do a Storage Verify on this Mofo.
        check_result_passed, check_result_message = manoward.storageJSONVerify(request.json)

        if check_result_passed is True:
            # It's good do the Storage
            this_store_collection_result = storage(g.config_items,
                                                   request.json,
                                                   sapi=True)

            data_dict = dict()
            data_dict["storage_result"] = this_store_collection_result
        else:
            g.logger.warning("Abnormal Check Result Storage Not Attempted : {}".format(
                check_result_message))

    if error is False:

        response_dict = dict()

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = data_dict
        response_dict["links"] = links_dict

    else:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

    return jsonify(**response_dict)
