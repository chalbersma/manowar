#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/ip/search/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Get the host(s) associated with this particular IP address
    responses:
      200:
        description: OK
    parameters:
      - name: ip
        in: query
        description: |
            The ipv4 or ipv6 address that you wish to search for records against.
        schema:
          type: string
      - name: subnet
        in: query
        description: |
            The ipv4 or ipv6 range of addresses that you wish to search against.
            this can be combined with ip but it's not reccomended as only the ip
            will match and only if it's in this range.
        schema:
          type: string
      - name: hostname
        in: query
        description: |
          The hostname you wish to search for. Is an exact match.
        schema:
          type: string
      - name: pop
        in: query
        description: |
          The pop you wish to search for. Is an exact match.
        schema:
          type: string
      - name: srvtype
        in: query
        description: |
          The srvtype you wish to search for. Is an exact match.
        schema:
          type: string
      - name: iptype
        in: query
        description: |
            Look for only one of the ips of this type.
        schema:
          type: string

```
"""

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import time
import ipaddress

ipsearch = Blueprint('api2_ipsearch', __name__)

@ipsearch.route("/ip/search", methods=['GET'])
@ipsearch.route("/ip/search/", methods=['GET'])
@ipsearch.route("/ip/search/<string:ip>", methods=['GET'])
@ipsearch.route("/ip/search/<string:ip>/", methods=['GET'])
def api2_ipsearch(ip=None, iptype=None, subnet=None, hostname=None, pop=None, srvtype=None):

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "IP Search Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"
    meta_info["children"] = dict()

    error_dict = dict()

    argument_error = False
    where_args = list()
    where_args_params = list()

    if "ip" in request.args :
        try:
            ip = ast.literal_eval(request.args["ip"])
        except Exception as e :
            argument_error = True
            error_dict["ip_parse_error"] = "Cannot Parse IP String"

    if ip != None and argument_error != True :
        try:
            validated_ip = str(ipaddress.ip_address(str(ip)))
        except ValueError as valerr :
            argument_error = True
            error_dict["fucked_ip"] = "Your IP is fucked {}".format(str(valerr))
        else :
            where_args.append(" ip_hex = INET6_ATON( %s )  ")
            where_args_params.append(str(validated_ip))

    if "subnet" in request.args :
        try:
            unvalidated_subnet = ast.literal_eval(request.args["subnet"])
            validated_subnet = ipaddress.ip_network(unvalidate_subnet)
            min_ip = validated_subnet[0]
            max_ip = validated_subnet[-1]
        except ValueError as valerr :
            argument_error = True
            error_dict["not_valid_subnet"] = "The subnet given was not valid"
        except Exception as e :
            argument_error = True
            error_dict["ip_parse_error"] = "Cannot Parse IP String"
        else :
            # Shit worked I now have a min and max IP
            where_args.append(" ip_hex > INET6_ATON( %s ) ")
            where_args_params.append(str(min_ip))
            where_args.append(" ip_hex < INET6_ATON( %s ) ")
            where_args_params.append(str(max_ip))

    if "iptype" in request.args :
        try:
            iptype = ast.literal_eval(request.args["iptype"])
        except Exception as e :
            argument_error = True
            error_dict["iptype_parse_error"] = "Cannot parse iptype"
        else:
            where_args.append(" guessed_type = %s ")
            where_args_params.append(str(iptype))

    if "hostname" in request.args :
        try:
            hostname = ast.literal_eval(request.args["hostname"])
        except Exception as e :
            argument_error = True
            error_dict["parsing_hostname_failed"] = "Cannot parse hostname"
        else :
            where_args.append(" hosts.hostname = %s ")
            where_args_params.append(str(hostname))

    if "pop" in request.args :
        try:
            pop = ast.literal_eval(request.args["pop"])
        except Exception as e :
            argument_error = True
            error_dict["parsing_pop_failed"] = "Cannot parse pop"
        else :
            where_args.append(" hosts.pop = %s ")
            where_args_params.append(str(pop))

    if "srvtype" in request.args :
        try:
            srvtype = ast.literal_eval(request.args["srvtype"])
        except Exception as e :
            argument_error = True
            error_dict["parsing_srvtype_failed"] = "Cannot parse srvtype"
        else :
            where_args.append(" hosts.srvtype = %s ")
            where_args_params.append(str(srvtype))

    if subnet == None and ip == None and hostname == None and pop == None and srvtype == None:
        argument_error = True
        error_dict["need_ip_address"] = "No IP address, hostname, pop, srvtypek or subnet given."


    requesttime=time.time()

    requesttype = "ipsearch"

    meta_info["request_tuple"] = ( ip, subnet, iptype )

    links_info = dict()

    links_info["self"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/ip/search"
    links_info["parent"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/ip/"
    links_info["children"] = dict()

    request_data = list()

    do_query = True

    where_args_params.append(str(g.twoDayTimestamp))
    where_args.append(" last_seen >= FROM_UNIXTIME( %s ) ")

    if len(where_args_params) > 0 :
        where_joiner = " where "
        where_clause_strings = " and ".join(where_args)
        where_full_string = where_joiner + where_clause_strings
    else :
        where_full_string = " "

    ip_search_query='''select
    INET6_NTOA(ip_hex) as ip,
    ip_id,
    guessed_type,
    fk_host_id,
    hosts.hostname,
    hosts.pop,
    hosts.srvtype,
    hosts.hoststatus
    from ip_intel
    join hosts on ip_intel.fk_host_id = hosts.host_id
    '''

    ip_search_query = ip_search_query + where_full_string


    # Select Query
    if do_query and argument_error == False :
        g.cur.execute(ip_search_query, where_args_params)
        all_ip_intel = g.cur.fetchall()
        amount_of_results = len(all_ip_intel)
    else :
        error_dict["do_query"] = "Query Ignored"
        amount_of_results = 0

    if amount_of_results > 0 :
        collections_good = True
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(all_ip_intel)) :
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = all_ip_intel[i]["ip_id"]
            this_results["attributes"] = all_ip_intel[i]
            this_results["relationships"] = dict()
            this_results["relationships"]["auditinfo"] = g.config_items["v2api"]["preroot"] + g.config_items["v2api"]["root"] + "/hostcollections/" + str(all_ip_intel[i]["fk_host_id"])

            # Now pop this onto request_data
            request_data.append(this_results)
    else :
        error_dict["ERROR"] = ["No Collections"]
        collections_good = False

    if collections_good :
        return jsonify(meta=meta_info, data=request_data, links=links_info)
    else :
        return jsonify(meta=meta_info, errors=error_dict, links=links_info)

