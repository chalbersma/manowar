#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from flask import current_app, Blueprint, g, request, jsonify, render_template
import json
import ast
import requests

display_collected_subtypes_filtered_search = Blueprint('display2_collected_subtypes_filtered_search', __name__)

@display_collected_subtypes_filtered_search.route("/collected/subtypes_filtered_search")
@display_collected_subtypes_filtered_search.route("/collected/subtypes_filtered_search/")
def display2_collected_subtypes_filtered_search(ctype="Insert type"):

	argument_error = False
	query_string_bits = list()

	if "ctype" in request.args :
		ctype = request.args["ctype"]

	return render_template('display_V2/collected_subtypes_filtered_search.html', ctype=ctype)


