#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''


from flask import current_app, Blueprint, g, request, jsonify
import json
import ast

from storageJSONVerify import storageJSONVerify
from storage import storage

puthostjson = Blueprint('puthostjson', __name__)

@puthostjson.route("/puthostjson", methods=['GET','POST'])
@puthostjson.route("/puthostjson/", methods=['GET','POST'])
def generic_puthostjson():

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    where_clauses = list()

    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish SAPI PutHostJSON "
    meta_dict["status"] = "In Progress"

    error=False

    if request.json == None :
        # No Json Data Given
        error_dict["nodata"] = True
        error=True


    #print(type(g.SCHEMAFILE))

    if error == False :

        # Do a Storage Verify on this Mofo.
        check_result=storageJSONVerify(g.SCHEMAFILE, request.json)

        # Parse Result
        check_result_passed=check_result[0]
        check_result_message=check_result[1]


        if check_result_passed is True :
            # It's good do the Storage
            this_store_collection_result = storage(g.STORAGECONFIG, request.json, sapi=True)

            data_dict=dict()
            data_dict["storage_result"] = this_store_collection_result

    if error == False :

        response_dict = dict()

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = data_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)

    else :

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
