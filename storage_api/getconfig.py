#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

getconfig/<audit_id>/buckets


Gives you a parsed json object that tells you what you should be collecting
for hosts that don't wish to manage collections by themselves.

```swagger-yaml
/getconfig/ : 
  get:
    produces:
      - application/json
    description: |
      Get's the ini file used in collections from the host.
    responses:
      200:
        description: OK
    parameters:       
```

'''

from flask import current_app, Blueprint, g, request, jsonify, abort, send_file
import json
import ast
import time
from configparser import ConfigParser


getconfig = Blueprint('sapi_getconfig', __name__)

@getconfig.route("/getconfig", methods=['GET'])
@getconfig.route("/getconfig/", methods=['GET'])
def sapi_getconfig():
	
	filename = g.COLLCONFIG["collection_config"]

	try: 
		return send_file(filename, "collection_config.ini")
	except Exception as e :
		print("Error with file ", filename , " : " , str(e) )  
		abort(500)
