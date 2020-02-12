#!/usr/bin/env python3


'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

/soc/vipporttohost endpoint
Allow the Soc to give us a vip (ipv4 or 6), a port and protocol (like tcp/22)

* And return a list of servers behind that vip that have that port and
    protocol over (over the last 2 days).

```swagger-yaml
/soc/vipporttohost/ :
  x-cached-length: "Every Midnight"
  get:
   description: |
     Grabs a list of hosts that are beind the given vip with the proper
     port/protocol open.
   tags:
     - liveaudit
   responses:
     200:
       description: OK
   parameters:
    - name: vip
      in: query
      description: |
        The VIP that you wish to search hosts against.
      required: true
      schema:
        type: string
      x-astliteraleval: true
    - name: port
      in: query
      description: |
        The port number that you wish to search against.
      schema:
        type: integer
      required: true
    - name: protocol
      schema:
        type: string
      in: query
      description: |
        This is a string that will accept `tcp` or `udp` (default is tcp)
        and use it in conjunction with the ports.
      required: false
    - name: ipv
      x-astliteraleval: true
      in: query
      description: |
        By default this will be `4` (as in ipv4). But you can set it to
        `6` which will allow you to look for ipv6 ports and protocols on
        ipv6 vips.
      schema:
        type: string
      required: false
```
'''


import json
import ast
import time
import os
import hashlib

from flask import current_app, Blueprint, g, request, jsonify, send_from_directory, abort


soc_vipporttohost = Blueprint('api2_soc_vipporttohost', __name__)


@soc_vipporttohost.route("/soc/vipporttohost", methods=['GET'])
@soc_vipporttohost.route("/soc/vipporttohost/", methods=['GET'])
def api2_soc_vipporttohost(ctype="none"):

    # TODO Rethink if this is needed.

    meta_dict = dict()
    request_data = list()
    links_dict = dict()
    error_dict = dict()
    relation_args = list()
    where_clauses = list()
    argument_error = False
    group_value = False

    # print(ctype)

    if "vip" in request.args:
        try:
            vip = ast.literal_eval(request.args["vip"])
        except Exception as e:
            error_dict["vip_read_error"] = "Error parsing vip : " + str(e)
            argument_error = True
    else:
        # VIP Required
        argument_error = True
        error_dict["no_vip"] = "Where my vip bro!"

    if "port" in request.args:
        try:
            port = int(ast.literal_eval(request.args["port"]))
            print(port)
        except Exception as e:
            error_dict["port_read_error"] = "Error parsing port filter" + \
                str(e)
            argument_error = True
        else:
            if type(port) != int:
                argument_error = True
                error_dict["port_type_error"] = "Error with port. Not an int()."
            elif port < 0:
                argument_error = True
                error_dict["port_invalid"] = "Error with port. Invalid Port."
    else:
        # Port Required
        argument_error = True
        error_dict["no_port"] = "Goddamn, give me a port baby."

    if "ipv" in request.args:
        try:
            ipv = ast.literal_eval(request.args["ipv"])
        except Exception as e:
            error_dict["ipv46_read_error"] = "Error parsing ipv directive" + \
                str(e)
            argument_error = True
        else:
            if type(ipv) != int:
                argument_error = True
                error_dict["ipv_type_error"] = "Error with ipv. Not an int()."
            elif ipv not in [4, 6]:
                argument_error = True
                error_dict["ip_version_invalid"] = "Error with ip version. Not a 4 or 6."
    else:
        # Default is IPV4
        ipv = 4

    if "protocol" in request.args:
        try:
            protocol = ast.literal_eval(request.args["protocol"])
        except Exception as e:
            error_dict["protocol_read_error"] = "Error parsing protocol filter" + \
                str(e)
            argument_error = True
        else:
            if protocol not in ["udp", "tcp"]:
                argument_error = True
                error_dict["protocol_error"] = "Protocol must be udp or tcp not : " + \
                    str(protocol)
    else:
        # Default is TCP
        protocol = "tcp"

    if argument_error != True:
        if ipv == 4:
            getSrvInfo_subtype = "vips"
            vips_type = "vips4"
            listen_string_tail = ""
        elif ipv == 6:
            getSrvInfo_subtype = "vips6"
            vips_type = "vips6"
            listen_string_tail = "6"
        listening_string = str(port)+"_"+protocol+listen_string_tail
        do_query = True
    else:
        do_query = False

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 : Soc Vip+Port to Host Query "
    meta_dict["status"] = "In Progress"
    meta_dict["NOW"] = g.NOW

    if argument_error == False:
        meta_dict["inputs"] = [vip, port, protocol, ipv]
        try:
            hash_string = " ".join([vip, str(port), protocol, str(ipv)])
            # To take into account the value grouping on cache
            cache_hash_object = hashlib.sha512(hash_string.encode())
            cache_string = cache_hash_object.hexdigest()
        except Exception as e:
            error_dict["cache_hash_error"] = "Error generating cache hash object" + \
                str(e)
            print("Error " + str(e))
            argument_error = True
        else:
            meta_dict["cache_hash"] = cache_string
            meta_dict["this_cached_file"] = g.config_items["v2api"]["cachelocation"] + \
                "/soc_vipporttohost_" + cache_string + ".json"

    links_dict["parent"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/soc"
    links_dict["self"] = g.config_items["v2api"]["preroot"] + \
        g.config_items["v2api"]["root"] + "/soc/vipporttohost/"

    requesttype = "soc_vipporttohost"

    # Check to see if a Cache File exists
    if argument_error is False and os.path.isfile(meta_dict["this_cached_file"]) is True:
        # There's a Cache File see if it's fresh
        cache_file_stats = os.stat(meta_dict["this_cached_file"])
        # Should be timestamp of file in seconds
        cache_file_create_time = int(cache_file_stats.st_ctime)

    if argument_error == True:
        do_query = False

    if do_query:
        # Means that the cache file doesn't exit or isn't fresh ADD: listening_string
        vipporttohost_args = [g.twoDayTimestamp,
                              listening_string, vips_type, vip, g.twoDayTimestamp]
        vipporttohost_query = '''SELECT hosts.host_id,
       hosts.hostname,
       hosts.hoststatus,
       hosts.pop,
       hosts.srvtype,
       UNIX_TIMESTAMP(collection.initial_update) AS initial_update,
       UNIX_TIMESTAMP(collection.last_update) AS last_update
FROM collection
JOIN hosts ON fk_host_id = hosts.host_id
WHERE collection.last_update >= FROM_UNIXTIME(%s)
  AND collection_type = 'listening'
  AND collection_subtype = %s
  AND fk_host_id IN
    (SELECT fk_host_id
     FROM collection
     WHERE collection_type=%s
       AND collection_subtype=%s
       AND last_update >= FROM_UNIXTIME(%s))'''

        print(vipporttohost_query)

    if do_query:
        g.cur.execute(vipporttohost_query, vipporttohost_args)
        hosts_matching = g.cur.fetchall()
        amount_of_hosts = len(hosts_matching)
    else:
        error_dict["do_query"] = "Query Ignored"
        amount_of_hosts = 0

    if amount_of_hosts > 0:
        # Hydrate the dict with type & ids to be jsonapi compliant
        for i in range(0, len(hosts_matching)):
            this_results = dict()
            this_results["type"] = requesttype
            this_results["id"] = i
            this_results["attributes"] = hosts_matching[i]

            # Now pop this onto request_data
            request_data.append(this_results)

        # Move onto the next one
        collections_good = True

    else:
        error_dict["ERROR"] = ["No Collections"]
        collections_good = False

    if collections_good:

        response_dict = dict()

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["data"] = request_data
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
    else:

        response_dict = dict()
        response_dict["meta"] = meta_dict
        response_dict["errors"] = error_dict
        response_dict["links"] = links_dict

        return jsonify(**response_dict)
