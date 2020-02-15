#!/usr/bin/env python3


"""
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
     port/protocol open. This is a rather specific endpoint for a particular cause.
     Given a VIP and a port/protocol that something was seen on. This will show
     you all the hosts associated with that vip that have that same port/protocol
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
      format: ipv46
    - name: port
      in: query
      description: |
        The port number that you wish to search against.
      schema:
        type: integer
      required: true
      default: 443
    - name: protocol
      schema:
        type: string
        enum:
          - udp
          - tcp
      in: query
      description: |
        This is a string that will accept `tcp` or `udp` (default is tcp)
        and use it in conjunction with the ports.
      required: false
      default: tcp
    - name: ipv
      in: query
      description: |
        By default this will be `4` (as in ipv4). But you can set it to
        `6` which will allow you to look for ipv6 ports and protocols on
        ipv6 vips.
      schema:
        type: integer
      required: false
      default: 4
```
"""

from flask import Blueprint, g, request, jsonify

import manoward

soc_vipporttohost = Blueprint('api2_soc_vipporttohost', __name__)


@soc_vipporttohost.route("/soc/vipporttohost", methods=['GET'])
@soc_vipporttohost.route("/soc/vipporttohost/", methods=['GET'])
def api2_soc_vipporttohost():
    """
    Do a Search for Hosts Associated with a particular VIP that have the requisite port open on the proper protocol.
    """

    args_def = {"vip": {"req_type": str,
                        "default": None,
                        "required": True,
                        "qdeparse": True,
                        "sql_param" : True,
                        "sql_clause": "ip_intel.ip_hex = INET6_ATON(%s)"
                        },
                "port": {"req_type": int,
                         "default": 443,
                         "required": True,
                         "qdeparse": True,
                         "positive": True},
                "protocol": {"req_type": str,
                             "default": "tcp",
                             "required": True,
                             "qdeparse": True,
                             "enum": ("udp", "tcp")},
                "ipv": {"req_type": int,
                        "default": 4,
                        "required": True,
                        "qdeparse": True,
                        "enum": (4, 6)}
                }

    args = manoward.process_args(args_def,
                                 request.args,
                                 include_exact=True,
                                 lulimit=g.twoDayTimestamp)

    meta_dict = dict()
    request_data = list()
    links_dict = dict()

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish API Version 2 : Soc Vip+Port to Host Query "
    meta_dict["status"] = "In Progress"
    meta_dict["NOW"] = g.NOW

    links_dict["parent"] = "{}{}/".format(g.config_items["v2api"]["preroot"],
                                          g.config_items["v2api"]["root"])

    links_dict["self"] = "{}{}/soc/vipporttothost/?{}".format(g.config_items["v2api"]["preroot"],
                                                              g.config_items["v2api"]["root"],
                                                              args["qdeparsed_string"])

    request_type = "soc_vipporttohost"

    ipv_sql = ""
    if args["ipv"] == 6:
        ipv_sql = 6

    args["args_clause"].append(" collection_subtype = %s")
    args["args_clause_args"].append("listening")
    args["args_clause"].append(" ip_intel.guessed_type = %s")
    args["args_clause_args"].append("vip{}".format(args["ipv"]))
    args["args_clause"].append(" collection_subtype = %s")
    args["args_clause_args"].append("{}{}_{}".format(args["protocol"],
                                                     ipv_sql,
                                                     args["port"]))

    vipporttohost_query = '''SELECT {},
                                    ip_intel.ip_id as ip_id,
                                    INET6_NTOA(ip_intel.ip_hex) as ip,
                                    ip_intel.guessed_type as guessed_type
                             FROM collection
                             JOIN hosts ON collection.fk_host_id = hosts.host_id
                             JOIN ip_intel on hosts.host_id = ip_intel.fk_host_id
                             WHERE {}'''.format(" , ".join([*g.host_data_columns,
                                                            *g.coll_data_columns]),
                                                " and ".join(args["args_clause"]))

    run_result = manoward.run_query(g.cur,
                                    vipporttohost_query,
                                    args["args_clause_args"],
                                    do_abort=True)

    for this_result in run_result.get("data", list()):
        this_results = dict()
        this_results["type"] = request_type
        this_results["id"] = this_result["ip_id"]
        this_results["attributes"] = this_result

        this_results["relationshipts"] = dict()
        this_results["all_vip_of_type"] = "{}{}/ip/search/?hostid={}&iptype={}".format(g.config_items["v2api"]["preroot"],
                                                                                       g.config_items["v2api"]["root"],
                                                                                       this_result["host_id"],
                                                                                       this_result["guessed_type"])

        request_data.append(this_results)

    return jsonify(meta=meta_dict, data=request_data, links=links_dict)
