#!/usr/bin/env python3

'''
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import ast

import requests
from flask import current_app, Blueprint, g, request, jsonify, render_template

display_cve_canonical_search = Blueprint(
    'display2_cve_canonical_search', __name__)


@display_cve_canonical_search.route("/cve_canonical_check/search")
@display_cve_canonical_search.route("/cve_canonical_check/search/")
def display2_cve_canonical_search():
    
    '''
    Displays the CVE Interface Page
    '''

    #argument_error = False
    #query_string_bits = list()

    return render_template('display_V2/cve_canonical_check_search.html')
