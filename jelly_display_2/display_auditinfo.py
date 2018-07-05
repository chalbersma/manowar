#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''


from flask import current_app, Blueprint, g, request, jsonify, render_template
import json

import ast
import requests

auditinfo = Blueprint('auditinfo', __name__)

@auditinfo.route("/auditinfo")
@auditinfo.route("/auditinfo/")
@auditinfo.route("/auditinfo/<int:audit_id>")
@auditinfo.route("/auditinfo/<int:audit_id>/")
def display2_auditinfo(audit_id="0"):
	
	argument_error=False
	meta_dict=dict()
	error_dict=dict()
	
	if "audit_id" in request.args :
		try:
			audit_id = ast.literal_eval(request.args["audit_id"])
		except Exception as e :
			error_dict["audit_id_check"] = "Failed with " + str(e)
			argument_error=True

	if argument_error == False :
		if type(audit_id) is int and audit_id > 0 :
			pass
		else :
			error_dict["audit_id_type_error"] = "Audit_ID isn't a positive integer : " + str(audit_id) + ". Shame on you."
			argument_error=True
			
	if argument_error == False :
		try:
			this_endpoint = "/v2/auditinfo/" + str(audit_id)
			this_private_endpoint = g.HTTPENDPOINT + this_endpoint
		except Exception as e:
			error_dict["query_string_error"] = "Error generating query string: " + str(e)
			argument_error = True
		else:
			meta_dict["Endpoint"] = this_endpoint
	
	api_error = False

	try:
		content = requests.get(this_private_endpoint).content
	except Exception as e:
		error_dict["Error Getting Endpoint"] = "Error getting endpoint: " + str(e)
		api_error=True
	else:
		try:
			content_string = content.decode("utf-8")
			content_object = ast.literal_eval(content_string)
		except Exception as e:
			api_error=True
			error_dict["Error Rendering API Content"] = "Error reading data from endpoint: " + str(e)
		
	if api_error :
		return render_template('error.html', error=error_dict)
	else:
		return render_template('display_V2/auditinfo.html', audit_id=audit_id, content=content_object, meta=meta_dict )
	
