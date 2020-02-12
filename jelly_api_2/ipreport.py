#!/usr/bin/env python3

"""
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

```swagger-yaml
/ip/report/ :
  x-cached-length: "Every Midnight"
  get:
    description: |
      Reports an ip/host intelligence for future querying. There's an undocumented
      feature that allows you to post a series of ip addresses into this
    responses:
      200:
        description: OK
    tags:
      - IP
    parameters:
      - name: ip
        in: query
        description: |
            The ipv4 or ipv6 address that you wish to record a record against.
        schema:
          type: string
          format: ipv46
        required: true
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

```
"""

import json
import ast
import ipaddress

import requests
from flask import current_app, Blueprint, g, request, jsonify

import manoward

ipreport = Blueprint('api2_ipreport', __name__)


@ipreport.route("/ip/report", methods=['GET', 'POST'])
@ipreport.route("/ip/report/", methods=['GET', 'POST'])
@ipreport.route("/ip/report/<int:hostid>", methods=['GET', 'POST'])
@ipreport.route("/ip/report/<int:hostid>/", methods=['GET', 'POST'])
def api2_ipreport(hostid=None):
    '''
    Insert an IP Report For the given hostid
    '''

    meta_dict = dict()
    data_dict = list()
    links_dict = dict()

    # Enable this after testing
    this_endpoint_endorsements = (
        ("conntype", "ipintel"), ("conntype", "ldap"), ("conntype", "whitelist"))

    manoward.process_endorsements(endorsements=this_endpoint_endorsements,
                                  session_endorsements=g.session_endorsements, ignore_abort=g.debug)

    args_def = {"hostid": {"req_type": int,
                           "default": hostid,
                           "required": True,
                           "positive": True,
                           "qdeparse": False,
                           "sql_param": True,
                           "sql_clause": " fk_host_id=%s "},
                "iptype": {"req_type": str,
                           "default": None,
                           "required": True,
                           "enum": ("vips4", "vips6", "host4", "host6", "drac4", "drac6", "netdev4", "netdev6", "unknown"),
                           "qdeparse": True,
                           "sql_param": True,
                           "sql_clause": " guessed_type=%s "},
                "ip": {"req_type": str,
                       "default": None,
                       "required": True,
                       "qdeparse": True,
                       "sql_param": True,
                       "sql_clause": " ip_hex=INET6_ATON(%s) "}}

    args = manoward.process_args(args_def,
                                 request.args)

    # Custom Validations
    try:
        this_ip = ipaddress.ip_address(args["ip"])
    except ValueError as bad_ip:
        self.logger.error("Unparsable IP {}".format(args["ip"]))
        self.logger.debug("Error: {}".format(bad_ip))
        abort(415)
    except Exception as general_error:
        self.logger.error("Unknown Error Parsing IP")
        self.logger.debug("Error: {}".format(general_error))
        abort(500)
    else:
        this_ip_good = True
        if this_ip.is_private:
            self.logger.debug("{} is a private address.".format(this_ip))
            this_ip_good = False
        elif this_ip.is_multicast:
            self.logger.debug("{} is a multicast address.".format(this_ip))
            this_ip_good = False
        elif this_ip.is_unspecified:
            self.logger.debug(
                "{} is a unspecified (RFC 5735 or 2373) address.".format(this_ip))
            this_ip_good = False
        elif this_ip.is_loopback:
            self.logger.debug("{} is a loopback address.".format(this_ip))
            this_ip_good = False
        elif this_ip.is_link_local:
            self.logger.debug("{} is a link_local address.".format(this_ip))
            this_ip_good = False
        elif this_ip.is_global is False:
            self.logger.debug("{} is not a Global IP Address.".format(this_ip))
            this_ip_good = False

        if this_ip_good is False:
            self.logger.error(
                "A Non-Usable Address, That's Okay I'll tell the client it's cool")

    meta_dict["version"] = 2
    meta_dict["name"] = "Jellyfish IP Report "
    meta_dict["status"] = "In Progress"
    links_dict["parent"] = "{}{}".format(
        g.config_items["v2api"]["preroot"], g.config_items["v2api"]["root"])
    links_dict["self"] = "{}{}/ip/report/{}?{}".format(g.config_items["v2api"]["preroot"], g.config_items["v2api"]["root"],
                                                       args["hostid"], args["qdeparsed_string"])
    links_dict["ip"] = "{}{}/ip/search?{}".format(g.config_items["v2api"]["preroot"], g.config_items["v2api"]["root"],
                                                  args["hostid"], args["qdeparsed_string"])

    error = False

    these_reports = list()

    update_record = '''INSERT INTO ip_intel
                       SET {}
                       ON DUPLICATE KEY
                       UPDATE last_seen = CURRENT_TIMESTAMP()
                    '''.format(" , ".join(args["args_clause"]))

    try:
        g.cur.execute(update_record, args["args_clause_args"])
    except Exception as insert_error:
        g.logger.error("Unable to Insert This Record.")
        g.logger.debug(insert_error)
        abort(500)
    else:
        g.logger.info("Successfully inserted IP Intel.")

    return jsonify(meta=meta_dict, success=True, links=links_dict)
