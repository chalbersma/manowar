#!/usr/bin/env python3

'''
Copyright 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import json
import ast

import requests
from flask import current_app, Blueprint, g, request, jsonify, render_template, abort

import manoward

display_swagger_ui = Blueprint('display_swagger', __name__)


@display_swagger_ui.route("/swagger")
@display_swagger_ui.route("/swagger/")
def display_swagger():
    
    '''
    Built in Swagger Viewer
    '''


    return render_template('display_V2/swagger.html')
