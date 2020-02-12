#!/usr/bin/env python3


'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/collected/types endpoint
Designed to grab information about information as it exists on the edge
(according to our latest collected data). 
* Returns a list of types on the server.

```swagger-yaml
/collected/types/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Grabs a list of types available in our collections. This is a slower query, so
      results are cached once at midnight. If you query times out it will finish up
      the query & caching on the server and then serve it to you next time you ask.
    responses:
      200:
        description: OK
    tags:
      - collections
```
'''

import json
import ast
import time
import os

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory

import manoward

collected_types = Blueprint('api2_collected_type', __name__)


@collected_types.route("/collected/types", methods=['GET'])
@collected_types.route("/collected/types/", methods=['GET'])
def api2_collected_types():

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 : Collected Types"
    meta_dict["status"] = "In Progress"

    links_dict["children"] = dict()
    links_dict["parent"] = "{}{}/collected".format(g.config_items["v2api"]["preroot"],
                                                   g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/collected/types".format(g.config_items["v2api"]["preroot"],
                                                       g.config_items["v2api"]["root"])

    requesttype = "collection_type"

    # Have a deterministic query so that query caching can do it's job
    collected_type_args = [g.twoDayTimestamp]
    collected_type_query = "select distinct(collection_type) from collection where last_update >= FROM_UNIXTIME(%s)"

    results = manoward.run_query(g.cur,
                                 collected_type_query,
                                 args=collected_type_args,
                                 one=False,
                                 do_abort=True,
                                 require_results=False)

    for this_ctype in results.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = None
        this_results["attributes"] = this_ctype

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
