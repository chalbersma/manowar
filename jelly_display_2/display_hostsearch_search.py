#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from flask import current_app, Blueprint, g, request, jsonify, render_template
import json
import ast
import requests

display_hostsearch_search = Blueprint('display2_hostsearch_search', __name__)

@display_hostsearch_search.route("/hostsearch/search")
@display_hostsearch_search.route("/hostsearch/search/")
def display2_hostsearch_search():

    argument_error = False
    query_string_bits = list()

    return render_template('display_V2/hostsearch_search.html')


