#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import ast

import requests
from flask import current_app, Blueprint, g, request, jsonify, render_template

display_collected_values_search = Blueprint(
    'display2_collected_values_search', __name__)


@display_collected_values_search.route("/collected/values_search")
@display_collected_values_search.route("/collected/values_search/")
def display2_collected_values_search(ctype="Insert type", csubtype="Insert Subtype"):
    
    '''
    Return the Collected Values Search Form
    '''

    if "ctype" in request.args:
        ctype = request.args["ctype"]

    if "csubtype" in request.args:
        csubtype = request.args["csubtype"]

    return render_template('display_V2/collected_values_search.html', ctype=ctype, csubtype=csubtype)
