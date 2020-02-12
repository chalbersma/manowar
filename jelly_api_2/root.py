#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/root/ :                                              
  x-cached-length: "Every Midnight"                  
  get:                                               
    description: |
      Get Information about All Jellyfish2 Endpoints
    responses:
      200:
        description: OK
```
"""

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import time

root = Blueprint('api2_root', __name__)


@root.route("/")
@root.route("/root")
@root.route("/root/")
def api2_root():

    root_meta_dict = dict()
    root_meta_dict["endorsements"] = g.session_endorsements
    root_meta_dict["restrictions"] = g.session_restrictions

    root_data_dict = dict()
    root_links_dict = dict()

    root_meta_dict["version"] = 2
    root_meta_dict["name"] = "Jellyfish2 API Version 2"
    root_meta_dict["state"] = "In Progress"

    root_links_dict["children"] = {"dashboard": (g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/dashboard"),
                                   "collected": (g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/collected"),
                                   "auditinfo": (g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/auditinfo")}

    root_links_dict["self"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/"

    return jsonify(data=root_data_dict, meta=root_meta_dict, links=root_links_dict)
