#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from flask import current_app, Blueprint, g, request, jsonify, render_template
import json
import ast
import requests

display_custdashboard_create = Blueprint('display2_custdashboard_create', __name__)

@display_custdashboard_create.route("/custdashboard/create")
@display_custdashboard_create.route("/custdashboard/create/")
def display2_custdashboard_create():

    argument_error = False
    query_string_bits = list()

    return render_template('display_V2/custdashboard_create.html')


