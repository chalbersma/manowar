#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from flask import current_app, Blueprint, g, request, jsonify, render_template
import json                                                                   
import ast                                                                    
import requests                                                               
                                                                              
hostsearchresults = Blueprint('hostsearchresults', __name__)                              
                                                                              
@hostsearchresults.route("/hostsearchresults")
@hostsearchresults.route("/hostsearchresults/")
def display2_hostsearchresults(exact=False, hostname=False, hoststatus=False, pop=False, srvtype=False):

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    query_string_bits = list()

    # Grab Values
    if "hostname" in request.args :
        try:
            hostname = ast.literal_eval(request.args["hostname"])
            query_string_bits.append("hostname='"+str(hostname)+"'")
        except Exception as e :
            error_dict["hostname_read_error"] = "Error parsing hostname " + str(e)
            argument_error=True

    if "hoststatus" in request.args :
        try:
            hoststatus = ast.literal_eval(request.args["hoststatus"])
            query_string_bits.append("hoststatus='"+str(hoststatus)+"'")
        except Exception as e :
            error_dict["hoststatus_read_error"] = "Error parsing hoststatus " + str(e)
            argument_error=True

    if "pop" in request.args :
        try:
            pop = ast.literal_eval(request.args["pop"])
            query_string_bits.append("pop='"+str(pop)+"'")
        except Exception as e :
            error_dict["pop_read_error"] = "Error parsing pop " + str(e)
            argument_error=True

    if "srvtype" in request.args :
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
            query_string_bits.append("srvtype='"+str(srvtype)+"'")
        except Exception as e :
            error_dict["srvtype_read_error"] = "Error parsing srvtype " + str(e)
            argument_error=True

    if "exact" in request.args :
        try:
            exact = ast.literal_eval(request.args["exact"])
        except Exception as e :
            error_dict["hostname_read_error"] = "Error parsing hostname " + str(e)
            argument_error=True
        else :
            if exact == True :
                query_string_bits.append("exact=True")

    if argument_error == False :
        try:
            query_string = "&".join(query_string_bits)
            this_endpoint = g.config_items["v2api"]["root"] + "/hostsearch/?" + query_string
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
        return render_template('error.html', error=error_dict)
        # Use my Template
    else:
        return render_template('display_V2/hostsearchresults.html', content=content_object, meta=meta_dict )


