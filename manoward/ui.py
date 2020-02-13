#!/usr/bin/env python3

'''
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import logging
#from configparser import ConfigParser
import argparse
import json
import ast
import time
import datetime
import os
import sys
import base64

from flask import Flask, current_app, g, request, render_template, abort
from flask_cors import CORS, cross_origin
import pymysql
import yaml


import manoward
import manoward.pull_swagger

from manoward.tokenmgmt import validate_key
from manoward.generic_large_compare import generic_large_compare


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-c", "--config", help="Config File for Scheduler", required=False, default=None)
    parser.add_argument("-d", "--flaskdebug", action='store_true',
                        help="Turn on Flask Debugging", default=False)
    parser.add_argument("-v", "--verbose", action='append_const',
                        help="Turn on Verbosity", const=1, default=[])

    args = parser.parse_args()

    VERBOSE = len(args.verbose)

    if VERBOSE == 0:
        logging.basicConfig(level=logging.ERROR)

    elif VERBOSE == 1:
        logging.basicConfig(level=logging.WARNING)

    elif VERBOSE == 2:
        logging.basicConfig(level=logging.INFO)

    elif VERBOSE > 2:
        logging.basicConfig(level=logging.DEBUG)

    LOGGER = logging.getLogger()

    LOGGER.info("Welcome to Man 'o War")

    FDEBUG = args.flaskdebug
    LOGGER.debug("Is Debug {}".format(FDEBUG))

    CONFIG = manoward.get_manoward(explicit_config=args.config,
                                   only_file=False)


def ui(CONFIG, FDEBUG):
    '''
    Main Function that Starts up the Flask Service.

    Reads Configs, loads individual api calls etc...
    '''

    _swagger_loc = "manoward/static/sw/swagger.json"

    logger = logging.getLogger("ui.ui")

    config_items = CONFIG

    logger.debug("Configuration Items: {}".format(config_items))

    if FDEBUG is True:
        logger.debug("Debug Mode, Updating Swagger Definitions")

        swaggerPieces = manoward.pull_swagger.generateSwaggerPieces(
            "jelly_api_2")

        manoward.pull_swagger.generateOutputFile(
            swaggerPieces["data"], _swagger_loc, "openapi3/openapi3.yml.jinja")

        logger.debug("Swagger written to {}".format(_swagger_loc))

    # Ensure Cache Dir is There, if not Make it
    cacheDir = config_items['v2api']['cachelocation']
    if not os.path.exists(cacheDir):
        try:
            os.makedirs(cacheDir)
        except Exception as e:
            logger.error(
                "Error creating cache dir {} with error: {}".format(cacheDir, e))
            return False

    # Create db_conn

    app = Flask(__name__)

    # Strict Slashes Flse
    app.url_map.strict_slashes = False

    # Enable CORS for UI Guys
    # Ad a config option for the domains
    CORS(app, supports_credentials=True, origins="pages.github.com")

    @app.before_request
    def before_request():
        try:

            g.db = manoward.get_conn(
                config_items, prefix="api_", tojq=".database", ac_def=True)

            g.logger = logger

            g.debug = FDEBUG

        except Exception as connection_error:
            logger.debug("Connection to DB Error Abandoing Connection Error.")

            return str(connection_error)

        # Endpoint Authorization List of Endosements and Restrictions that Define what you may and may not access
        # For endpoints with fine grained controls

        g.session_endorsements = list()
        g.session_restrictions = list()

        # Open a New Cursor for this Request
        # Get Username
        username = "local_or_ip_whitelist"

        try:
            auth_header = request.headers.get("Authorization")
            uname_pass_64 = auth_header.split()[1]
            decoded_uname_pass = base64.b64decode(
                uname_pass_64).decode("utf-8")
            username = decoded_uname_pass.split(":")[0]

        except Exception as no_auth_error:
            logger.debug(
                "No Authentication token given, either local access or IP whitelist : {}".format(no_auth_error))
            username = "local_or_ip_whitelist"
            g.session_endorsements.append(("conntype", "whitelist"))
            g.session_restrictions.append(("conntype", "whitelist"))

            logger.warning("Local Flask or Whitelist IP detected.")

        else:

            # Parsing was successful add ldap endorsment
            g.session_endorsements.append(("conntype", "ldap"))
            g.session_restrictions.append(("conntype", "ldap"))

        finally:
            logger.debug("User {} Connected a Session.".format(username))
            g.USERNAME = username

        # Robot Authentication
        try:
            robot_header = ast.literal_eval(
                request.headers.get("robotauth", "False"))

            logger.debug("Robot Header : {}".format(robot_header))

            if robot_header is True:
                # I need to do robot auth
                username, apikey = auth_header.split(':')

                g.USERNAME = username

                auth_cursor = g.db.cursor(pymysql.cursors.DictCursor)

                # Integrating Token Types. For now new tokens types will be processed
                # here. In the future this "endorsements" section will be replaced
                # with logic to look at our new centralized authorization system.

                anyvalid = False
                for tokentype in ["robot", "sapi", "ipintel"]:

                    key_valid = validate_key(
                        username=username, giventoken=apikey, dbcur=auth_cursor, tokentype=tokentype)

                    print(tokentype, key_valid)

                    if key_valid is True:
                        # Add Robots Endorsement and Restriction
                        g.session_endorsements.append(("conntype", tokentype))
                        g.session_restrictions.append(("conntype", tokentype))
                        anyvalid = True
                        # No break loop
                        break
                if anyvalid is False:
                    # No Valid Token was found
                    logger.warning("Robot Token Out of Date.")
                    abort(403)

                auth_cursor.close()

            else:
                # This isn't a robot call
                pass
        except AttributeError as attribute_error:
            logger.error(
                "Attribute Error parsing Robot Items. Killing. {}".format(attribute_error))
            abort(403)
        except SyntaxError as syntax_error:
            logger.error(
                "Syntax Error parsing Robot Items. Killing. {}".format(syntax_error))
            abort(500)
        finally:
            pass

        # Default Endorsement
        g.session_endorsements.append(("username", "{}".format(g.USERNAME)))

        # DEFAULT Fresh. Use this instead of "Fresh" Values to allow for query caching.
        NOW = int(time.time())
        seconds_after_midnight = NOW % 86400
        MIDNIGHT = NOW - seconds_after_midnight
        oldest = MIDNIGHT - (86400*2)

        g.NOW = NOW
        g.MIDNIGHT = MIDNIGHT
        g.twoDayTimestamp = oldest

        # DB Columns
        g.host_data_columns = ["hosts.host_id as host_id",
                               "hosts.host_uber_id as host_uber",
                               "hosts.hostname as hostname",
                               "hosts.pop as pop",
                               "hosts.srvtype as srvtype",
                               "hoststatus", "UNIX_TIMESTAMP(hosts.last_update) as hlast_update",
                               "hosts.mresource as resource",
                               "hosts.mpartition as mpartition", # Partition is a Reserved Word in mariadb
                               "hosts.mservice as service",
                               "hosts.mregion as region",
                               "hosts.maccountid as accountid",
                               "hosts.mownbase",
                               "hosts.mownfull",
                               "hosts.mowntags"]

        g.cur = g.db.cursor(pymysql.cursors.DictCursor)
        g.HTTPENDPOINT = config_items["webserver"]["accesslink"]
        g.config_items = config_items

        logger.debug("Current Session Endorsements : {}".format(
            g.session_endorsements))

    @app.after_request
    def after_request(response):
        # Add CORS Header
        #response.headers["Access-Control-Allow-Credentials"] = "true"
        # Close My Cursor JK Do that in teardown request
        return response

    @app.teardown_request
    def teardown_request(response):
        # Get Rid of My Cursor
        cur = getattr(g, 'cur', None)
        if cur is not None:
            cur.close()
        db = getattr(g, 'db', None)
        if db is not None:
            db.close()
        return response

    # API 2 Imports
    from jelly_api_2 import root
    from jelly_api_2 import dashboard
    from jelly_api_2 import collected_root
    from jelly_api_2 import collected_types
    from jelly_api_2 import collected_subtypes
    from jelly_api_2 import collected_values
    from jelly_api_2 import auditinfo
    from jelly_api_2 import auditinfo_buckets
    from jelly_api_2 import auditresults
    from jelly_api_2 import auditresults_timestamp
    from jelly_api_2 import auditresults_range
    from jelly_api_2 import hostcollections
    from jelly_api_2 import collated
    from jelly_api_2 import collected_subtypes_filtered
    from jelly_api_2 import soc_vipporttohost
    from jelly_api_2 import sapi_listusers
    from jelly_api_2 import sapi_adduser
    from jelly_api_2 import sapi_addtoken
    from jelly_api_2 import hostsearch
    from jelly_api_2 import custdashboard_list
    from jelly_api_2 import custdashboard_dashboard
    from jelly_api_2 import custdashboard_create
    from jelly_api_2 import custdashboard_modify
    from jelly_api_2 import auditlist
    from jelly_api_2 import factorlist
    from jelly_api_2 import cve_canonical
    from jelly_api_2 import genericlargecompare
    from jelly_api_2 import cve_canonical_check
    #from jelly_api_2 import getconfig
    from jelly_api_2 import puthostjson
    from jelly_api_2 import extendpopulationjson
    from jelly_api_2 import ipsearch
    from jelly_api_2 import ipreport

    # Display for Jelly 2 API
    from jelly_display_2 import display_auditinfo
    from jelly_display_2 import display_auditresults
    from jelly_display_2 import display_hostcollections
    from jelly_display_2 import display_collected_values
    from jelly_display_2 import display_collected_subtype_filtered
    from jelly_display_2 import display_collected_values_search
    from jelly_display_2 import display_collected_subtypes_filtered_search
    from jelly_display_2 import display_soc_vipporttohost
    from jelly_display_2 import display_soc_vipporttohost_search
    from jelly_display_2 import display_auditslist
    from jelly_display_2 import display_hostsearchresults
    from jelly_display_2 import display_custdashboard_create
    from jelly_display_2 import display_custdashboard_modify
    #from jelly_display_2 import display_custdashboard_create_results
    from jelly_display_2 import display_hostsearch_search
    from jelly_display_2 import display_cve_canonical_check_results
    from jelly_display_2 import display_cve_canonical_search
    from jelly_display_2 import display_collatedresults
    from jelly_display_2 import display_mainfactor
    from jelly_display_2 import display_custdashboardlist
    from jelly_display_2 import display_dashboard
    from jelly_display_2 import display_swagger_ui

    # Register API Blueprints for Version 2
    app.register_blueprint(root.root, url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(dashboard.dashboard,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(collected_root.collected_root,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(collected_types.collected_types,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(collected_subtypes.collected_subtypes,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(collected_values.collected_values,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(auditinfo.auditinfo,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(auditinfo_buckets.auditinfo_buckets,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(auditresults.auditresults,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(auditresults_timestamp.auditresults_timestamp,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(auditresults_range.auditresults_range,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(hostcollections.hostcollections,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(
        collated.collated, url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(collected_subtypes_filtered.collected_subtypes_filtered,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(soc_vipporttohost.soc_vipporttohost,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(sapi_listusers.sapi_listusers,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(sapi_adduser.sapi_adduser,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(sapi_addtoken.sapi_addtoken,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(hostsearch.hostsearch,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(custdashboard_list.custdashboard_list,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(custdashboard_dashboard.custdashboard_dashboard,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(custdashboard_create.custdashboard_create,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(custdashboard_modify.custdashboard_modify,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(auditlist.auditlist,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(factorlist.factorlist,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(cve_canonical.cve_canonical,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(genericlargecompare.genericlargecompare,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(cve_canonical_check.cve_canonical_check,
                           url_prefix=config_items["v2api"]["root"])
    # No Longer A Thing that Makes General & Good Sense
    #app.register_blueprint(getconfig.getconfig, url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(puthostjson.puthostjson,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(extendpopulationjson.extendpopulationjson,
                           url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(
        ipsearch.ipsearch, url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(
        ipreport.ipreport, url_prefix=config_items["v2api"]["root"])

    # Register Display
    app.register_blueprint(display_auditresults.auditresults,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_auditinfo.auditinfo,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_hostcollections.hostcollections,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_collected_values.display_collected_values,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_collected_subtype_filtered.display_subtypes_filtered,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_collected_values_search.display_collected_values_search,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_collected_subtypes_filtered_search.display_collected_subtypes_filtered_search,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_soc_vipporttohost.display_soc_vipporttohost,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_soc_vipporttohost_search.display_soc_vipporttohost_search,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_auditslist.auditslist,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_hostsearchresults.hostsearchresults,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_custdashboard_create.display_custdashboard_create,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_custdashboard_modify.display_custdashboard_modify,
                           url_prefix=config_items["v2ui"]["root"])
    #app.register_blueprint(display_custdashboard_create_results.display_custdashboard_create_results, url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_hostsearch_search.display_hostsearch_search,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_cve_canonical_check_results.display_cve_canonical_check_results,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_cve_canonical_search.display_cve_canonical_search,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_collatedresults.collatedresults,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_mainfactor.mainfactor,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_custdashboardlist.custdashboardlist,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_dashboard.dashboard,
                           url_prefix=config_items["v2ui"]["root"])
    app.register_blueprint(display_swagger_ui.display_swagger_ui,
                           url_prefix=config_items["v2ui"]["root"])

    @app.template_filter('ctime')
    def timectime(s):
        return time.ctime(s)

    @app.template_filter('firstx')
    def firstx(s, x):
        return s[:x]

    @app.route("/")
    def index():
        # Index
        return render_template("index.html")

    app.run(debug=FDEBUG,
            port=int(config_items['webserver']['port']),
            threaded=True,
            host=config_items['webserver']['bindaddress'])


# Run if Execute from CLI
if __name__ == "__main__":

    ui(CONFIG, FDEBUG)
