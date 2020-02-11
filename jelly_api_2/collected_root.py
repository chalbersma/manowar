#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/collected endpoint
Designed as the root point for all the collected endpoints

```swagger-yaml
/collected/ :
  get:
    description: |
      Root for the collected endpoint. Describes it's child for data discovery.
    tags:
      - collections
    responses:
      200:
       description: OK
```
'''

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import time


collected_root = Blueprint('api2_collected_root', __name__)


@collected_root.route("/collected", methods=['GET'])
@collected_root.route("/collected/", methods=['GET'])
def api2_collected_root():

    root_meta_dict = dict()
    root_data_dict = dict()
    root_links_dict = dict()

    root_meta_dict["version"] = 2
    root_meta_dict["name"] = "Jellyfish API Version 2 : Collected "
    root_meta_dict["status"] = "In Progress"

    root_links_dict["children"] = {"types": (
        g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected/types")}
    root_links_dict["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"]
    root_links_dict["self"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/collected"

    return jsonify(data=root_data_dict, meta=root_meta_dict, links=root_links_dict)
