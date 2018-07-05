#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# Storage API Pass a JSON and win big.

from configparser import ConfigParser
import argparse
from flask import Flask, current_app, g, request, render_template, abort
import pymysql
import json
import ast
import time
import datetime

from storageJSONVerify import storageJSONVerify
from storage import storage
from tokenmgmt import validate_key

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", help="Config File for Scheduler", required=True)
    parser.add_argument("-d", "--flaskdebug", action='store_true', help="Turn on Flask Debugging")
    parser._optionals.title = "DESCRIPTION "

    args = parser.parse_args()

    FDEBUG=args.flaskdebug
    CONFIG=args.configfile


def ui(CONFIG, FDEBUG):

    this_time=int(time.time())
    back_week=this_time-604800
    back_month=this_time-2628000
    back_quarter=this_time-7844000
    back_year=this_time-31540000
    back_3_year=this_time-94610000
    time_defaults={ "now" : str(this_time), "weekago" : str(back_week), "monthago" : str(back_month), "quarterago" : str(back_quarter), "yearago" : str(back_year), "threeyearago" : str(back_3_year) }


    try:
        # Read Our INI with our data collection rules
        config = ConfigParser(time_defaults)
        config.read(CONFIG)
        # Debug
        #for i in config :
            #for key in config[i] :
                #print (i, "-", key, ":", config[i][key])
    except Exception as e: # pylint: disable=broad-except, invalid-name
        sys.exit('Bad configuration file {}'.format(e))

    # Grab me Collections Items Turn them into a Dictionary
    config_items=dict()

    # Collection Items
    for section in config :
        config_items[section]=dict()
        for item in config[section]:
            config_items[section][item] = config[section][item]



    # Debug
    #print(config_items)

    # Create db_conn

    app = Flask(__name__)

    @app.before_request
    def before_request():
        try :
            g.db = pymysql.connect(host=config_items['database']['dbhostname'], \
                                port=int(config_items['database']['dbport']), \
                                user=config_items['database']['dbusername'], \
                                passwd=config_items['database']['dbpassword'], \
                                db=config_items['database']['dbdb'], \
                                autocommit=False )
            dbmessage = "Good, connected to " + config_items['database']['dbusername'] + "@" + config_items['database']['dbhostname'] + ":" + config_items['database']['dbport'] + "/" + config_items['database']['dbdb']
        except Exception as e :
            dbmessage = "Connection Failed connected to " + config_items['database']['dbusername'] + "@" + config_items['database']['dbhostname'] + ":" + config_items['database']['dbport'] + "/" + config_items['database']['dbdb'] + " With Error " + str(e)
            return dbmessage
        # Open a New Cursor for this Request
        g.cur = g.db.cursor(pymysql.cursors.DictCursor)

        g.APITOKENTYPE = config_items["authentication"]["tokentype"]
        header_token = request.headers.get("Authorization", default="nobody:nothing")

        username, apikey = header_token.split(':')

        key_valid = validate_key(username=username, giventoken=apikey, dbcur=g.cur, tokentype=g.APITOKENTYPE)

        if key_valid == True :
            # Continue
            pass
        else :
            # Fail
            abort(403)

        g.HTTPENDPOINT = config_items["webserver"]["accesslink"]
        g.STORAGECONFIG = config_items["storage"]["storeconfig"]
        g.SCHEMAFILE = config_items["verification"]["json_schema_file"]
        g.EXTENDSCHEMAFILE = config_items["verification"]["extension_schema_file"]
        g.COLLCONFIG = config_items["collections"]
        g.ROBOTENDPOINT = config_items["apiaccess"]["apilocation"]
        g.robotstoken={ "Authorization" : "{}:{}".format(config_items["apiaccess"]["apiusername"], config_items["apiaccess"]["apitoken"]) }
        g.MAXCHARS = config_items["storage"]["storeconfig_maxchars"]

    @app.after_request
    def after_request(response) :
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
            db.commit()
            db.close()
        return response






    # Import Blue Print Files
    ## API Imports
    from storage_api import puthostjson
    from storage_api import getconfig
    from storage_api import extendpopulationjson

    # Register API Blueprints
    app.register_blueprint(puthostjson.puthostjson, url_prefix="/sapi")
    app.register_blueprint(getconfig.getconfig, url_prefix="/sapi")
    app.register_blueprint(extendpopulationjson.extendpopulationjson, url_prefix="/sapi")

    app.run(debug=FDEBUG, port=int(config_items['webserver']['port']), threaded=True)


# Run if Execute from CLI
if __name__ == "__main__":
    ui(CONFIG, FDEBUG)
