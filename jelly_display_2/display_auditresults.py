#!/usr/bin/env python3

'''Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from flask import current_app, Blueprint, g, request, jsonify, render_template
import json                                                                   
import ast                                                                    
import requests                                                               
                                                                              
auditresults = Blueprint('auditresults', __name__)                              
                                                                              
@auditresults.route("/auditresults")                                            
@auditresults.route("/auditresults/")
@auditresults.route("/auditresults/<int:audit_id>")                                 
@auditresults.route("/auditresults/<int:audit_id>/")
def display2_auditresults(audit_id=0, hostname=False, pop=False, srvtype=False, bucket=False, auditResult=False, auditResultText=False, status=False):

	meta_dict = dict()
	request_data = list()
	links_dict = dict()
	error_dict = dict()
	
	argument_error = False
	query_string_bits = list()
	
	# Grab Values
	if "audit_id" in request.args :
		try: 
			audit_id = ast.literal_eval(request.args["audit_id"])
		except Exception as e : 
			print("Exception")
			error_dict["audit_id_read_error"] = "Error parsing audit_id " + str(e)
			argument_error=True

	if argument_error == False :
		if type(audit_id) is int and audit_id > 0 :
			query_string_bits.append("audit_id="+str(audit_id))
		else :
			error_dict["audit_id_type_error"] = "Audit_ID isn't a positive integer : " + str(audit_id) + ". Shame on you."
			argument_error=True
				
	# Grab Additional Values
	if "hostname" in request.args :
		try:
			hostname = ast.literal_eval(request.args["hostname"])
		except Exception as e :
			error_dict["hostname_read_error"] = "Error parsing hostname " + str(e)
			argument_error=True
		else:
			this_clause = "hostname='"+hostname+"'"
			query_string_bits.append(this_clause)
			
	if "pop" in request.args :
		try: 
			pop = ast.literal_eval(request.args["pop"])
		except Exception as e : 
			error_dict["pop_read_error"] = "Error parsing pop " + str(e)
			argument_error=True
		else:
			this_clause = "pop='"+pop+"'"
			query_string_bits.append(this_clause)
			
	if "status" in request.args :
		try: 
			status = ast.literal_eval(request.args["status"])
		except Exception as e : 
			error_dict["status_read_error"] = "Error parsing status " + str(e)
			argument_error=True
		else:
			this_clause = "status='"+status+"'"
			query_string_bits.append(this_clause)		
			
	if "srvtype" in request.args :
		try: 
			srvtype = ast.literal_eval(request.args["srvtype"])
		except Exception as e : 
			error_dict["srvtype_read_error"] = "Error parsing srvtype " + str(e)
			argument_error=True
		else:
			this_clause = "srvtype='"+srvtype+"'"
			query_string_bits.append(this_clause)
			
	if "bucket" in request.args :
		try: 
			bucket = ast.literal_eval(request.args["bucket"])
		except Exception as e : 
			error_dict["bucket_read_error"] = "Error parsing bucket " + str(e)
			argument_error=True
		else:
			this_clause = "bucket='"+bucket+"'"
			query_string_bits.append(this_clause)
			
	if "auditResult" in request.args :
		try: 
			auditResult = ast.literal_eval(request.args["auditResult"])
		except Exception as e : 
			error_dict["auditResult_read_error"] = "Error parsing auditResult " + str(e)
			argument_error=True
		else: 
			this_clause = "auditResult='"+auditResult+"'"
			query_string_bits.append(this_clause)
			
	if "auditResultText" in request.args :
		try: 
			auditResultText = ast.literal_eval(request.args["auditResultText"])
		except Exception as e : 
			error_dict["auditResultText_read_error"] = "Error parsing auditResultText " + str(e)
			argument_error=True
		else:
			this_clause = "auditResultText='"+auditResultText+"'"
			query_string_bits.append(this_clause)
			
			
	if argument_error == False :
		try:
			query_string = "&".join(query_string_bits)
			this_endpoint = "/v2/auditresults?" + query_string
			this_private_endpoint = g.HTTPENDPOINT + this_endpoint
		except Exception as e:
			error_dict["query_string_error"] = "Error generating query string: " + str(e)
			argument_error = True
		else:
			meta_dict["Endpoint"] = this_endpoint
			
	# Grab Endpoint

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
		# Use my Template
	else:
		return render_template('display_V2/auditresults.html', audit_id=audit_id, content=content_object, meta=meta_dict )
		

