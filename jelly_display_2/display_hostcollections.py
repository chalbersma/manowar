#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from flask import current_app, Blueprint, g, request, jsonify, render_template
import json                                                                   
import ast                                                                    
import requests                                                               
                                                                              
hostcollections = Blueprint('hostcollections', __name__)                              
                                                                              
@hostcollections.route("/hostcollections")                                            
@hostcollections.route("/hostcollections/")                                           
@hostcollections.route("/hostcollections/<int:host_id>")                                 
@hostcollections.route("/hostcollections/<int:host_id>/")                                
def display2_hostcollections(host_id=0, collection_type=False, collection_subtype=False):

	meta_dict = dict()
	request_data = list()
	links_dict = dict()
	error_dict = dict()
	
	argument_error = False
	query_string_bits = list()
	
	# Grab Values
	if "host_id" in request.args :
		try: 
			host_id = ast.literal_eval(request.args["host_id"])
		except Exception as e : 
			print("Exception")
			error_dict["host_id_read_error"] = "Error parsing host_id " + str(e)
			argument_error=True

	if argument_error == False :
		if type(host_id) is int and host_id > 0 :
			query_string_bits.append("host_id="+str(host_id))
		else :
			error_dict["host_id_type_error"] = "Host_ID isn't a positive integer : " + str(host_id) + ". Shame on you."
			argument_error=True
				
	# Grab Additional Values
	if "collection_type" in request.args :
		try:
			collection_type = ast.literal_eval(request.args["collection_type"])
		except Exception as e :
			error_dict["collection_type_read_error"] = "Error parsing collection_type " + str(e)
			argument_error=True
		else:
			this_clause = "collection_type='"+collection_type+"'"
			query_string_bits.append(this_clause)
			
	if "collection_subtype" in request.args :
		try: 
			collection_subtype = ast.literal_eval(request.args["collection_subtype"])
		except Exception as e : 
			error_dict["collection_subtype_read_error"] = "Error parsing collection_subtype " + str(e)
			argument_error=True
		else:
			this_clause = "collection_subtype='"+collection_subtype+"'"
			query_string_bits.append(this_clause)
			
	if argument_error == False :
		try:
			query_string = "&".join(query_string_bits)
			this_endpoint = g.config_items["v2api"]["root"] + "/hostcollections?" + query_string
			this_private_endpoint = g.HTTPENDPOINT + this_endpoint
		except Exception as e:
			error_dict["query_string_error"] = "Error generating query string: " + str(e)
			argument_error = True
		else:
			meta_dict["Endpoint"] = str(g.config_items["v2api"]["preroot"]) + this_endpoint
			
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
			content_object = json.loads(content_string)
		except Exception as e:
			api_error=True
			error_dict["Error Rendering API Content"] = "Error reading data from endpoint: " + str(e)
		
	if api_error :
		#print(error_dict)
		return render_template('error.html', error=error_dict)
		# Use my Template
	else:
		return render_template('display_V2/hostcollections.html', host_id=host_id, content=content_object, meta=meta_dict )
		

