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
    parameters:
      - name: ip
        in: query
        description: |
            The ipv4 or ipv6 address that you wish to record a record against.
        schema:
          type: string
        required: true
      - name: iptype
        in: query
        description: |
            Look for only one of the ips of this type. Must be vips4, vips6, host4,
            host6, drac4, drac6, netdev4, netdev6 or unknown.
        schema:
          type: string
        required: true
      - name: hostname
        in: query
        description: |
            Hostname to associate this host with. You need either this or a host
            id to be a valid report.
        schema:
          type: string

```
"""

from flask import current_app, Blueprint, g, request, jsonify
import json
import ast
import endorsementmgmt
import ipaddress
import requests



ipreport = Blueprint('api2_ipreport', __name__)

@ipreport.route("/ip/report", methods=['GET','POST'])
@ipreport.route("/ip/report/", methods=['GET','POST'])
def api2_ipreport():

    meta_dict = dict()
    data_dict = list()
    links_dict = dict()
    error_dict = dict()

    # Enable this after testing
    this_endpoint_endorsements = ( ("conntype","ipintel"),("conntype","ldap"),("conntype","whitelist") )

    endorsementmgmt.process_endorsements(endorsements=this_endpoint_endorsements, \
                                session_endorsements=g.session_endorsements, ignore_abort=g.debug)

    argument_error = False
    where_clause_args = list()
    where_clause_params = list()

    meta_dict["version"]  = 2
    meta_dict["name"] = "Jellyfish IP Report "
    meta_dict["status"] = "In Progress"

    error=False

    these_reports = list()

    if request.json == None :
        # Not given a jscript of the things
        collect_from_query_args = True
    else :
        # I've been given a js via post
        collect_from_query_args = False
        these_reports = request.json

    if collect_from_query_args :
        if "ip" in request.args :
            try:
                ip = ast.literal_eval(request.args["ip"])
            except Exception as e :
                argument_error = True
                error_dict["ip_parse_error"] = "Cannot Parse IP String"
        else:
            argument_error = True
            error_dict["no_ip_given"] = "No IP Was given in report."

        if "iptype" in request.args :
            try:
                iptype = ast.literal_eval(request.args["iptype"])
            except Exception as e:
                argument_error = True
                error_dict["unable_to_parse_iptype"] = "Cannot parse ip type"
            else :
                if type(iptype) is not str :
                    argument_error = True
                    error_dict["odd_iptype"] = "Shit's weird homie."
                else :
                    # It's good
                    if iptype not in ['vips4','vips6','host4','host6','drac4',\
                                    'drac6','netdev4','netdev6','unknown'] :
                        argument_error = True
                        error_dict["unsupported_ip_type"] = "Unsupported IP Type"
                    else :
                        # IP Type is good
                        pass
            this_record = { "ip" : ip, "iptype" : iptype }
            these_reports.append(this_record)
        else:
            # No IP Type Given
            argument_error = True
            error_dict["no_iptype"] = "Missing an iptype for your report."



    if "hostname" in request.args :
        try:
            hostname = ast.literal_eval(request.args["hostname"])
        except Exception as e :
            argument_error = True
            error_dict["hostid_parse_error"] = "Cannot Parse hostid"
        else:
            if type(hostname) is not str :
                argument_error = True
                error_dict["bad_hostname"] = "hostname do not look right. Not a string."
            else :
                # It's a string!
                hostid_get_query_args = dict()
                hostid_get_query_args["hostname"] = "'{}'".format(hostname)
                hostid_get_query_args["exact"] = "True"

                hostid_endpoint = g.config_items["v2api"]["root"] + "/hostsearch/?"
                hostid_private_endpoint = "{}{}/hostsearch/?".format(g.HTTPENDPOINT, g.config_items["v2api"]["root"])

                try:
                    hostid_request = requests.get(hostid_private_endpoint, params=hostid_get_query_args)
                    hostid_json = hostid_request.json()
                except Exception as e:
                    argument_error = True
                    error_dict["error_getting_hostid"] = "Error getting hostid: {}".format(str(e))
                else:
                    # Parse dat shit
                    if "errors" in hostid_json.keys() :
                        argument_error = True
                        error_dict["no_host"] = "No Host found"
                        error_dict["more_no_host_details"] = hostid_json["errors"]
                    else :
                        # Got that data bitch!
                        # Only take the first result. If there's dupes that's a problem but it should be relatively transient.
                        this_host = hostid_json["data"][0]
                        hostid = this_host["id"]
    else:
        argument_error = True
        error_dict["no_hostname_given"] = "No Hostname was given in the report."

    bad_reports = list()
    good_reports = list()

    if argument_error == False :

        for unvalidated_report in these_reports:
            this_failed = False
            try:
                validated_ip = ipaddress.ip_address(unvalidated_report["ip"])
            except ValueError as valerr :
                # Fail this Report
                this_failed = True
            else :
                if unvalidated_report["iptype"] not in ['vips4','vips6', \
                                        'host4','host6','drac4', \
                                        'drac6','netdev4','netdev6','unknown'] :
                    this_failed = True
            finally :
                if this_failed == True :
                    bad_reports.append(unvalidated_report)
                else :
                    good_reports.append(unvalidated_report)

        meta_dict["bad_reports"] = bad_reports

    # Now It's time to figure out if I'm updateing
    find_existing_query = '''SELECT ip_id from ip_intel
        where ip_hex = INET6_ATON(%s) and
        fk_host_id = %s and
        guessed_type  = %s '''

    if argument_error == False :

        for this_record in good_reports :

            this_ip = this_record["ip"]
            this_iptype = this_record["iptype"]

            try:
                g.cur.execute(find_existing_query, (this_ip, hostid, this_iptype) )
            except Exception as e :
                error = True
                error_dict["error_for_existing"] = str(e)
            else :
                # It's okay
                rows_found = g.cur.rowcount
                if rows_found == 0 :
                    # No Row Found do Insert
                    addnew_query = '''REPLACE INTO ip_intel ( ip_hex, fk_host_id, guessed_type )
                    VALUES( INET6_ATON( %s ), %s, %s )'''
                    try:
                        #print(g.cur.mogrify(addnew_query, (this_ip, hostid, this_iptype) ))
                        g.cur.execute(addnew_query, (this_ip, hostid, this_iptype) )
                    except Exception as e :
                        error = True
                        error_dict["insert_error"] = str(e)
                    else :
                        data_dict.append({"New":this_record})
                else :
                    # Get ID
                    results = g.cur.fetchone()
                    ip_intel_id = results["ip_id"]
                    # Update Query
                    update_query = '''UPDATE ip_intel set last_seen = CURRENT_TIMESTAMP where ip_id = %s '''
                    try:
                        g.cur.execute(update_query, (ip_intel_id) )
                    except Exception as e :
                        error = True
                        error_dict["Update_Report_Error"] = str(e)
                    else :
                        data_dict.append({"Update":this_record})

        # Now do my Commit
        g.db.commit

    else :
        error_dict["Argument_Error"] = True
        error = True

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
