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

mainfactor = Blueprint('mainfactor', __name__)

@mainfactor.route("/mainfactor")
@mainfactor.route("/mainfactor/")
@mainfactor.route("/mainfactor/<string:mainfactor>")
@mainfactor.route("/mainfactor/<string:mainfactor>/")
def display2_collatedresults(mainfactor=False, with_other=None, with_hostname=None, with_status=None, exact=False):

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    query_string_bits = dict()

    # Grab Values
    if "mainfactor" in request.args :
        try:
            mainfactor = ast.literal_eval(request.args["mainfactor"])
        except Exception as e :
            error_dict["mainfactor_read_error"] = "Error parsing mainfactor " + str(e)
            argument_error=True

    if mainfactor == False or mainfactor not in ["pop", "srvtype"] :
        # Shit wrong bro!
        argument_error = True
        error_dict["mainfactor_missing"] = "Hey!"
    else :
        # It's an old endpoint but it checks out.
        endpoint_name = "{}list".format(str(mainfactor))
        if mainfactor == "pop" :
            other_is = "with_srvtype"
        elif mainfactor == "srvtype" :
            other_is = "with_pop"
        else :
            # Dafuq homie
            argument_error = True
            error_dict["mainfactor_missing"] = "The wizardry is real!."


    if "with_other" in request.args :
        try:
            with_other = ast.literal_eval(request.args["with_other"])
            query_string_bits[other_is] = "'{}'".format(str(with_other))
        except Exception as e :
            error_dict["withother_read_error"] = "Error parsing with other " + str(e)
            argument_error=True

    if "with_hostname" in request.args :
        try:
            with_hostname = ast.literal_eval(request.args["with_hostname"])
            query_string_bits["with_hostname"] = "'{}'".format(str(with_hostname))
        except Exception as e :
            error_dict["withhostname_read_error"] = "Error parsing hostname " + str(e)
            argument_error=True

    if "with_status" in request.args :
        try:
            with_status = ast.literal_eval(request.args["with_status"])
            query_string_bits["with_status"] = "'{}'".format(str(with_status))
        except Exception as e :
            error_dict["withstatus_read_error"] = "Error parsing status " + str(e)
            argument_error=True

    if "exact" in request.args :
        try:
            exact = ast.literal_eval(request.args["exact"])
            if exact == True :
                query_string_bits["exact"] = "True"
        except Exception as e :
            error_dict["withstatus_read_error"] = "Error parsing status " + str(e)
            argument_error=True

    if argument_error == False :
        try:
            query_string = urllib.parse.urlencode(query_string_bits)
            this_endpoint = g.config_items["v2api"]["root"] + "/{}/?".format(endpoint_name) + query_string
            this_private_endpoint = g.HTTPENDPOINT + this_endpoint
        except Exception as e:
            error_dict["query_string_error"] = "Error generating query string: " + str(e)
            argument_error = True
        else:
            meta_dict["Endpoint"] = str(g.config_items["v2api"]["preroot"]) + this_endpoint

    # Grab Endpoint
    if argument_error == False :
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
    else :
        api_error = True

    if api_error :
        return render_template('error.html', error=error_dict)
        # Use my Template
    else:
        return render_template('display_V2/mainfactor.html', content=content_object, meta=meta_dict, mainfactor=mainfactor )


