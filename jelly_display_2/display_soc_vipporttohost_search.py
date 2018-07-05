#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from flask import current_app, Blueprint, g, request, jsonify, render_template
import json
import ast
import requests

display_soc_vipporttohost_search = Blueprint('display2_soc_vipporttohost_search', __name__)

@display_soc_vipporttohost_search.route("/soc/vipporttohost_search")
@display_soc_vipporttohost_search.route("/soc/vipporttohost_search/")
def display2_collected_subtypes_filtered_search(ctype="Insert type"):

    argument_error = False
    query_string_bits = list()

    if "ctype" in request.args :
        ctype = request.args["ctype"]

    return render_template('display_V2/soc_vipporttohost_search.html', ctype=ctype)


