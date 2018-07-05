#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''


from flask import current_app, Blueprint, g, request, jsonify, render_template
import json                                                                   
import ast                                                                    
import requests                                                               
                                                                              
display_collected_values = Blueprint('display2_collected_values', __name__)                              
                                                                              
@display_collected_values.route("/collected/values")                                            
@display_collected_values.route("/collected/values/")                                           
@display_collected_values.route("/collected/values/<string:ctype>", methods=['GET'])
@display_collected_values.route("/collected/values/<string:ctype>/", methods=['GET'])
@display_collected_values.route("/collected/values/<string:ctype>/<string:csubtype>", methods=['GET'])
@display_collected_values.route("/collected/values/<string:ctype>/<string:csubtype>/", methods=['GET'])                
def display2_collected_values(ctype="none", csubtype="none"):

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    query_string_bits = list()

    if "ctype" in request.args :
        try:
            ctype = ast.literal_eval(request.args["ctype"])
        except Exception as e :
            error_dict["ctype_read_error"] = "Error Parsing Collection Type"
            argument_error = True

    if "csubtype" in request.args :
        try:
            csubtype = ast.literal_eval(request.args["csubtype"])
        except Exception as e :
            error_dict["csubtype_read_error"] = "Error Parsing Collection Subtype"
            argument_error = True

    query_string_bits.append("ctype='"+ctype+"'")
    query_string_bits.append("csubtype='"+csubtype+"'")

    if "hostname" in request.args :
        try:
            hostname = ast.literal_eval(request.args["hostname"])
            query_string_bits.append("hostname='"+hostname+"'")
        except Exception as e :
            error_dict["hostname_read_error"] = "Error parsing hostname " + str(e)
            argument_error=True

    if "pop" in request.args :
        try:
            pop = ast.literal_eval(request.args["pop"])
            query_string_bits.append("pop='"+pop+"'")
        except Exception as e :
            error_dict["pop_read_error"] = "Error parsing pop " + str(e)
            argument_error=True

    if "status" in request.args :
        try:
            status = ast.literal_eval(request.args["status"])
            query_string_bits.append("status='"+status+"'")
        except Exception as e :
            error_dict["status_read_error"] = "Error parsing status " + str(e)
            argument_error=True

    if "srvtype" in request.args :
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
            query_string_bits.append("srvtype='"+srvtype+"'")
        except Exception as e :
            error_dict["srvtype_read_error"] = "Error parsing srvtype " + str(e)
            argument_error=True

    if "value" in request.args :
        try:
            value = ast.literal_eval(request.args["value"])
            query_string_bits.append("value='"+value+"'")
        except Exception as e :
            error_dict["value_read_error"] = "Error parsing value " + str(e)
            argument_error=True

    # Gen query string
    if argument_error == False :
        try:
            query_string = "&".join(query_string_bits)
            meta_dict["query_string"] = query_string
            this_endpoint = g.config_items["v2api"]["root"] + "/collected/values/?" + query_string
            this_private_endpoint = g.HTTPENDPOINT + this_endpoint
        except Exception as e:
            error_dict["query_string_error"] = "Error generating query string: " + str(e)
            argument_error = True
        else:
            meta_dict["Endpoint"] = str(g.config_items["v2api"]["preroot"]) + this_endpoint
            meta_dict["ctype"] = str(ctype)
            meta_dict["csubtype"] = str(csubtype)

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
        print(error_dict)
        return render_template('error.html', error=error_dict)
        # Use my Template
    else:
        return render_template('display_V2/collected_values.html', content=content_object, meta=meta_dict )


