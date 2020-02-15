#!/usr/bin/env python3

"""
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/sapi/extendpopulationjson/ :
  get:
    description: |
      Allows you to "extend" a host or population of hosts with new data. Gives a generic way
      to insert new collections for an existing host.
    responses:
      200:
        description: OK
      401:
        description: Unauthorized (Most likely no Token given)
    tags:
      - sapi
    requestBody:
      content:
        application/json:
          required: true
          schema:
            type: object
    parameters:
      - name: host_id
        in: path
        description: |
          The id of a specific host you'd like to use. If this is specified the hostname & collection type arguments
          that can be used to specify a population are ignored.
        schema:
          type: integer
        required: false
      - name: ctype
        in: query
        description: |
          A regex to match for the collection_type. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
          regular expressions are accepted. Matched on the collection_type column in the collection table.
          Only hosts with one or more results of this collection type will be returned.
        schema:
          type: string
        required: false
      - name: ictype
        in: query
        description: |
          The name of the collection type you'd like to record. "Inserted" collection type.
        schema:
          type: string
        required: true
      - name: icsubtype
        in: query
        description: |
          The name of the collection subtype type you'd like to record. "Inserted" collection subtype.
        schema:
          type: string
        required: true
      - name: ivalue
        in: query
        description: |
          The value you'd like to record. "Inserted" value.
        schema:
          type: string
        required: true
      {{ exact | indent(6, True) }}
      {{ col | indent(6, True) }}
      {{ hosts | indent(6, True) }}
```
"""

import urllib.parse

import requests

import manoward

from flask import current_app, Blueprint, g, request, jsonify, abort

from manoward.storage import insert_update_collections


extendpopulationjson = Blueprint('extendpopulationjson', __name__)


@extendpopulationjson.route("/extendpopulationjson", methods=['GET'])
@extendpopulationjson.route("/extendpopulationjson/", methods=['GET'])
@extendpopulationjson.route("/sapi/extendpopulationjson", methods=['GET'])
@extendpopulationjson.route("/sapi/extendpopulationjson/", methods=['GET'])
@extendpopulationjson.route("/sapi/extendpopulationjson/<int:hostid>", methods=['GET'])
@extendpopulationjson.route("/sapi/extendpopulationjson/<int:hostid>/", methods=['GET'])
def generic_extendpopulationjson(hostid=None):
    '''
    General idea, give me a collection type, subtype & value to insert for a host or a population
    of hosts and I will "do the needful"

    Two Step Process, Search Population. Insert Data
    '''

    this_endpoint_endorsements = (("conntype", "sapi"), )

    manoward.process_endorsements(endorsements=this_endpoint_endorsements,
                                  session_endorsements=g.session_endorsements,
                                  ignore_abort=g.debug)

    args_def = {"hostid": {"req_type": int,
                           "default": hostid,
                           "required": False,
                           "positive": True,
                           "sql_param": True,
                           "sql_clause": " hosts.host_id = %s ",
                           "qdeparse": True},
                "ctype": {"req_type": str,
                          "default": None,
                          "required": False,
                          "sql_param": True,
                          "sql_clause": "collection.collection_type REGEXP %s",
                          "sql_exact_clause": "collection.collection_type = %s",
                          "qdeparse": True},
                "ictype": {"req_type": str,
                           "default": None,
                           "required": True,
                           "qdeparse": True},
                "icsubtype": {"req_type": str,
                              "default": None,
                              "required": True,
                              "qdeparse": True},
                "ivalue": {"req_type": str,
                           "default": None,
                           "required": True,
                           "qdeparse": True}
                }

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_hosts_sql=True,
                                 include_coll_sql=True,
                                 include_exact=True)


    meta_dict = dict()
    request_data = list()
    links_dict = dict()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish SAPI Extend Population JSON "
    meta_dict["status"] = "In Progress"

    links_dict["self"] = "{}{}/extendpopulationjson/?{}".format(g.config_items["v2api"]["preroot"],
                                                                g.config_items["v2api"]["root"],
                                                                args["qdeparsed_string"])

    population = list()

    if args["hostid"] is not None:

        links_dict["population_query"] = "{}/v2/hostsearch/?hostid={}".format(g.ROBOTENDPOINT,
                                                                              args["hostid"])

        population = [args["hostid"]]

    else:
        links_dict["population_query"] = "{}/v2/hostsearch/?{}".format(g.ROBOTENDPOINT,
                                                                       args["common_qdeparsed_string"])

        try:
            pop_result = requests.get(links_dict["population_query"]).json()

            population = [host["id"]
                          for host in pop_result.get("data", list())]

        except Exception as population_query_error:
            g.logger.error("Unable to Query for Population")
            g.logger.debug("{}".format(population_query_error))
            abort(500)
        else:
            meta_dict["population_size"] = len(population)

    host_data_to_insert = {"collection_data": {args["ictype"]: {args["icsubtype"]: args["ivalue"]}},
                           "collection_timestamp": g.NOW}

    inserted_qdeparsed_string = urllib.parse.urlencode({"ctype" : args["ictype"],
                                                        "csubtype" : args["csubtype"],
                                                        "value" : args["ivalue"]})

    for this_hostid in population:

        this_extend_collection = dict()
        extention_results = insert_update_collections(g.db,
                                                                                                                                                this_hostid,
                                                                                                                                                host_data_to_insert,
                                                                                                                                                g.config_items["storage"].get("collectionmaxchars", 255))
        this_extend_collection["attributes"] = dict(inserts=extention_results[0],
                                                    updates=extention_results[1],
                                                    errors=extention_results[2])

        this_extend_collection["id"] = this_hostid
        this_extend_collection["relationships"] = dict()

        this_extend_collection["relationships"]["collections"] = "{}{}/hostcollections/{}/?{}".format(g.config_items["v2api"]["preroot"],
                                                                                                      g.config_items["v2api"]["root"],
                                                                                                      this_hostid,
                                                                                                      inserted_qdeparsed_string)

        request_data.append(this_extend_collection)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
