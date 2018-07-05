#!/usr/bin/env python3


'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import requests

from storageJSONVerify import storageJSONVerify
from storage import insert_update_collections

extendpopulationjson = Blueprint('extendpopulationjson', __name__)

@extendpopulationjson.route("/extendpopulationjson", methods=['GET','POST'])
@extendpopulationjson.route("/extendpopulationjson/", methods=['GET','POST'])
def generic_extendpopulationjson(hostname=False, exact=False, pop=False,\
                        hoststatus=False, status=False):

    '''
    General idea, give me a population and a json object and I'll update everything
    in that population with that data.
    '''

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()

    argument_error = False
    where_clauses = list()

    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish SAPI Extend Population JSON "
    meta_dict["status"] = "In Progress"

    query_args = dict()

    # Grab Values
    if "hostname" in request.args :
        try:
            hostname = ast.literal_eval(request.args["hostname"])
            query_args["hostname"] = "'{}'".format(str(hostname))
        except Exception as e :
            error_dict["hostname_read_error"] = "Error parsing hostname " + str(e)
            argument_error=True

    if "exact" in request.args :
        try:
            exact = ast.literal_eval(request.args["exact"])
            query_args["exact"] = "True"
        except Exception as e :
            error_dict["exact_read_error"] = "Error parsing exact " + str(e)
            argument_error=True

    if "pop" in request.args :
        try:
            pop = ast.literal_eval(request.args["pop"])
            query_args["pop"] = "'{}'".format(str(pop))
        except Exception as e :
            error_dict["pop_read_error"] = "Error parsing pop " + str(e)
            argument_error=True

    if "srvtype" in request.args :
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
            query_args["srvtype"] = "'{}'".format(str(srvtype))
        except Exception as e :
            error_dict["srvtype_read_error"] = "Error parsing srvtype " + str(e)
            argument_error=True

    havestatus = False
    if "hoststatus" in request.args :
        try:
            hoststatus = ast.literal_eval(request.args["hoststatus"])
            havestatus = True
        except Exception as e :
            error_dict["hoststatus_read_error"] = "Error parsing status " + str(e)
            argument_error=True
    elif "status" in request.args :
        try:
            hoststatus = ast.literal_eval(request.args["status"])
            havestatus = True
        except Exception as e :
            error_dict["status_read_error"] = "Error parsing status " + str(e)
            argument_error=True

    if havestatus == True :
        query_args["hoststatus"] = "'{}'".format(str(hoststatus))

    error=False

    if argument_error == False :
        # Got my population variables, let's grab my population
        this_endpoint = "{}/v2/hostsearch/".format(g.ROBOTENDPOINT)

        meta_dict["population_endpoint"] = this_endpoint

        try :
            content = requests.get(this_endpoint, headers=g.robotstoken, params=query_args)
            population_response = content.json()

            if "errors" in population_response.keys() :
                error=True
                error_dict["errors in population query"] = population_response["errors"]
            else :
                population = population_response["data"]
        except Exception as e :
            error_dict["issues_with_population"] = "Unable to query for population : {}".format(str(e))
            error = True
        else :
            # It worked continue
            meta_dict["population_size"] = len(population)

    else :
        error = True

    if request.json == None :
        # No Json Data Given
        error_dict["nodata"] = True
        error=True



    if error == False :

        # Do a Storage Verify on this Mofo.
        check_result=storageJSONVerify(g.EXTENDSCHEMAFILE, request.json)

        # Parse Result
        check_result_passed=check_result[0]
        check_result_message=check_result[1]


        if check_result_passed is True :
            # I have my population at population
            # I have my Content at request.json

            # It's good do the Storage
            for host in population :


                this_extend_collection = insert_update_collections(g.db, host["id"], \
                                            request.json["collections"], g.MAXCHARS, \
                                            request.json["timestamp"], \
                                            host["attributes"]["hostname"] )

                this_result_thing = { "id" : host["id"],
                                      "hostname" : host["attributes"]["hostname"],
                                      "attributes" : this_extend_collection }

                request_data.append(this_result_thing)
        else :
            error = True
            error_dict["json_data_validation_fail"] = "Validating Json data failed with : {}".format(str(check_result_message))

    if error == False :

        response_dict = dict()

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = request_data
        response_dict["links"] = links_dict

        return jsonify(**response_dict)

    else :

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
