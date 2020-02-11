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
    tags:
      - IP
    parameters:
      - name: ip
        in: query
        description: |
            The ipv4 or ipv6 address that you wish to search for records against.
        schema:
          type: string
          format: ipv46
      - name: subnet
        in: query
        description: |
            The ipv4 or ipv6 range of addresses that you wish to search against.
            this can be combined with ip but it's not reccomended as only the ip
            will match and only if it's in this range.
        schema:
          type: string
          format: subnet46
      - name: iptype
        in: query
        description: |
            Look for only one of the ips of this type. Must be vips4, vips6, host4,
            host6, drac4, drac6, netdev4, netdev6 or unknown.
        schema:
          type: string
          enum:
            - vips4
            - vips6
            - host4
            - host6
            - drac4
            - drac6
            - netdev4
            - netdev6
            - unknown
        required: true
      - name: hostid
        in: query
        description: |
          hostid to search for
        schema:
          type: int
      {{ hosts | indent(6, True) }}
      {{ exact | indent(6, True) }}
```
"""

import json
import ast
import time
import ipaddress

from flask import current_app, Blueprint, g, request, jsonify, abort

import manoward

ipsearch = Blueprint('api2_ipsearch', __name__)


@ipsearch.route("/ip/search", methods=['GET'])
@ipsearch.route("/ip/search/", methods=['GET'])
@ipsearch.route("/ip/search/<string:ip>", methods=['GET'])
@ipsearch.route("/ip/search/<string:ip>/", methods=['GET'])
def api2_ipsearch(ip=None):
    '''
    Given a IP or Subnet, Search for that Thing and Return it.
    Can Filter by items in the standards hosts column.

    Respects Exact
    '''

    args_def = {"hostid": {"req_type": int,
                           "default": None,
                           "required": False,
                           "positive": True,
                           "sql_param": True,
                           "sql_clause": " fk_host_id=%s "},
                "iptype": {"req_type": str,
                           "default": None,
                           "required": False,
                           "enum": ("vips4", "vips6", "host4", "host6", "drac4", "drac6", "netdev4", "netdev6", "unknown"),
                           "qdeparse": True,
                           "sql_param": True,
                           "sql_clause": " guessed_type=%s "},
                "ip": {"req_type": str,
                       "default": ip,
                       "required": False,
                       "qdeparse": True,
                       "sql_param": True,
                       "sql_clause": " ip_hex=INET6_ATON(%s) "},
                "subnet": {"req_type": str,
                           "default": None,
                           "required": False,
                           "qdeparse": True,
                           "sql_param": False}  # Custom Handling for this
                }

    args = manoward.process_args(args_def,
                                 request.args,
                                 lulimit=g.twoDayTimestamp,
                                 include_hosts_sql=True,
                                 include_exact=True)

    meta_info = dict()
    meta_info["version"] = 2
    meta_info["name"] = "IP Search Jellyfish2 API Version 2"
    meta_info["state"] = "In Progress"

    # Custom Handle Subnet
    if args.get("subnet", None) is not None:
        try:
            validated_subnet = ipaddress.ip_network(args["subnet"])
            min_ip = validated_subnet[0]
            max_ip = validated_subnet[-1]
        except ValueError as valerr:
            logger.error(
                "Unable to Validate Subnet given with error : {}".format(valerr))
            abort(415)
        except Exception as general_error:
            logger.error(
                "General Error when validating Subnet : {}".format(general_error))
            abort(500)
        else:
            args["args_clause"].append(" ip_hex > INET6_ATON( %s ) ")
            args["args_clause_args"].append(str(min_ip))
            args["args_clause"].append(" ip_hex < INET6_ATON( %s ) ")
            args["args_clause_args"].append(str(max_ip))

    if args.get("subnet", None) is None and args.get("ip", None) is None:
        g.logger.warning(
            "No IP Given : This might be a Long Query but I'll allow it.")

        if args.get("hostid", None) is None and args.get("hostname", None) is None:
            g.logger.warning(
                "No Host Factor Given : This might be a Long Query but I'll allow it.")

    requesttype = "ipsearch"

    links_info = dict()

    links_info["parent"] = "{}{}/ip".format(g.config_items["v2api"]["preroot"],
                                            g.config_items["v2api"]["root"])
    links_info["self"] = "{}{}/ip/search?{}".format(g.config_items["v2api"]["preroot"],
                                                    g.config_items["v2api"]["root"],
                                                    args["qdeparsed_string"])

    request_data = list()

    ip_search_query = '''select
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
                        where {}'''.format(" and ".join(args["args_clause"]))

    results = manoward.run_query(g.cur,
                                 ip_search_query,
                                 args=args["args_clause_args"],
                                 one=False,
                                 do_abort=True,
                                 require_results=False)

    for this_ip in results.get("data", list()):
        this_results = dict()
        this_results["type"] = requesttype
        this_results["id"] = this_ip["ip_id"]
        this_results["attributes"] = this_ip
        this_results["relationships"] = dict()

        # Now pop this onto request_data
        request_data.append(this_results)

    return jsonify(meta=meta_info, data=request_data, links=links_info)
