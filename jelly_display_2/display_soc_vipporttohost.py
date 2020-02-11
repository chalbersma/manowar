#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import ast

import requests
from flask import current_app, Blueprint, g, request, jsonify, render_template

display_soc_vipporttohost = Blueprint('display2_soc_vipporttohost', __name__)


@display_soc_vipporttohost.route("/soc/vipporttohost", methods=['GET', 'POST'])
@display_soc_vipporttohost.route("/soc/vipporttohost/", methods=['GET', 'POST'])
def display2_soc_vipporttohost(vip=None, port=None, ipv=None, protocol=None):
    
    '''
    Display Collected Values
    
    TODO Modernize
    '''

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    query_string_bits = list()

    if "vip" in request.args:
        vip = ast.literal_eval(request.args["vip"])
    elif "vip" in request.form:
        vip = str(request.form["vip"])
    else:
        argument_error = True

    viparg = "vip='" + vip + "'"
    query_string_bits.append(viparg)

    if "port" in request.args:
        port = int(ast.literal_eval(request.args["port"]))
    elif "port" in request.args:
        port = int(request.form["port"])
    else:
        argument_error = True

    portarg = "port=" + str(port)
    query_string_bits.append(portarg)

    if "ipv" in request.args:
        ipv = int(ast.literal_eval(request.args["ipv"]))
    elif "ipv" in request.form:
        ipv = int(request.form["ipv"])
    else:
        # Default
        ipv = 4

    ipvarg = "ipv=" + str(ipv)
    query_string_bits.append(ipvarg)

    if "protocol" in request.args:
        protocol = ast.literal_eval(request.args["protocol"])
    elif "protocol" in request.form:
        protocol = str(request.form["protocol"])
    else:
        # Set Default
        protocol = "tcp"

    tcparg = "protocol='"+protocol+"'"
    query_string_bits.append(tcparg)

    # Gen query string
    if argument_error == False:
        try:
            query_string = "&".join(query_string_bits)
            meta_dict["query_string"] = query_string
            this_endpoint = g.config_items["v2api"]["root"] + \
                "/soc/vipporttohost/?" + query_string
            this_private_endpoint = g.HTTPENDPOINT + this_endpoint
        except Exception as e:
            error_dict["query_string_error"] = "Error generating query string: " + \
                str(e)
            argument_error = True
        else:
            meta_dict["Endpoint"] = str(
                g.config_items["v2api"]["preroot"]) + this_endpoint
            meta_dict["this_vip"] = vip
            meta_dict["this_port"] = port
            meta_dict["this_ipv"] = ipv
            meta_dict["this_protocol"] = protocol

    api_error = False

    try:
        content = requests.get(this_private_endpoint).content
    except Exception as e:
        error_dict["Error Getting Endpoint"] = "Error getting endpoint: " + \
            str(e)
        api_error = True
    else:
        try:
            content_string = content.decode("utf-8")
            content_object = json.loads(content_string)
        except Exception as e:
            api_error = True
            error_dict["Error Rendering API Content"] = "Error reading data from endpoint: " + \
                str(e)

    if api_error:
        print(error_dict)
        return render_template('error.html', error=error_dict)
        # Use my Template
    else:
        return render_template('display_V2/soc_vipporttohost.html', content=content_object, meta=meta_dict)
