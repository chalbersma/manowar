#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from flask import current_app, Blueprint, g, request, jsonify, render_template
import json
import ast
import requests
import urllib

collatedresults = Blueprint('collatedresults', __name__)

@collatedresults.route("/collatedresults")
@collatedresults.route("/collatedresults/")
@collatedresults.route("/collatedresults/<string:collatedType>")
@collatedresults.route("/collatedresults/<string:collatedType>/")
def display2_collatedresults(collatedType=False, typefilter=False, auditID=False):

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    query_string_bits = dict()

    # Grab Values
    if "collatedType" in request.args :
        try:
            collatedType = ast.literal_eval(request.args["collatedType"])
        except Exception as e :
            error_dict["collatedType_read_error"] = "Error parsing collatedType " + str(e)
            argument_error=True

    if collatedType != False :
        query_string_bits["collatedType"] = "'{}'".format(str(collatedType))
    else :
        # Not Specified
        argument_error = False
        error_dict["need_collated_type"] = "Give me the collated type."

    if "typefilter" in request.args :
        try:
            typefilter = ast.literal_eval(request.args["typefilter"])
            query_string_bits["typefilter"] = "'{}'".format(str(typefilter))
        except Exception as e :
            error_dict["typefilter_read_error"] = "Error parsing typefilter " + str(e)
            argument_error=True

    if "auditID" in request.args :
        try:
            auditID = ast.literal_eval(request.args["auditID"])
            query_string_bits["auditID"] = auditID
        except Exception as e :
            error_dict["auditID_read_error"] = "Error parsing auditID " + str(e)
            argument_error=True

    if argument_error == False :
        try:
            query_string = urllib.parse.urlencode(query_string_bits)
            this_endpoint = g.config_items["v2api"]["root"] + "/collated/?" + query_string
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
        return render_template('display_V2/collatedresults.html', content=content_object, meta=meta_dict, collatedType=collatedType, typefilter=typefilter )


