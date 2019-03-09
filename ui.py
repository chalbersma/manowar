#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

from configparser import ConfigParser
import argparse
from flask import Flask, current_app, g, request, render_template, abort
from flask_cors import CORS, cross_origin
import base64
import pymysql
import json
import ast
import time
import datetime
import os
from tokenmgmt import validate_key
from canonical_cve import shuttlefish
from generic_large_compare import generic_large_compare

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--configfile", help="Config File for Scheduler", required=True)
    parser.add_argument("-d", "--flaskdebug", action='store_true', help="Turn on Flask Debugging")
    parser._optionals.title = "DESCRIPTION "

    args = parser.parse_args()

    FDEBUG=args.flaskdebug
    CONFIG=args.configfile


def ui(CONFIG, FDEBUG):

    try:
        # Read Our INI with our data collection rules
        config = ConfigParser()
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

    # Ensure Cache Dir is There, if not Make it
    cacheDir = config_items['v2api']['cachelocation']
    if not os.path.exists(cacheDir):
        try:
            os.makedirs(cacheDir)
        except Exception as e:
            print("Error creating cache dir " + str(cacheDir) + " with error: " + str(e))
            return False

    # Create db_conn

    app = Flask(__name__)

    # Strict Slashes Flse
    app.url_map.strict_slashes = False

    # Enable CORS for UI Guys
    # Ad a config option for the domains
    cors = CORS(app, supports_credentials=True, origins="pages.github.com" )
    #cors = CORS(app,  support_credentials=True)


    # Before my First Request, Please attempt to Connect to the Database
    '''
    @app.before_first_request
    def test_database() :
        try :
            g.db = db_conn = pymysql.connect(host=config_items['database']['dbhostname'], port=int(config_items['database']['dbport']), user=config_items['database']['dbusername'], passwd=config_items['database']['dbpassword'], db=config_items['database']['dbdb'] )
            dbmessage = "Good, connected to " + config_items['database']['dbusername'] + "@" + config_items['database']['dbhostname'] + ":" + config_items['database']['dbport'] + "/" + config_items['database']['dbdb']
        except Exception as e :
            dbmessage = "Connection Failed connected to " + config_items['database']['dbusername'] + "@" + config_items['database']['dbhostname'] + ":" + config_items['database']['dbport'] + "/" + config_items['database']['dbdb'] + " With Error " + str(e)
            if __name__ == "__main__":
                print(dbmessage)
                exit
            return dbmessage
        if __name__ == "__main__" :
            print(dbmessage)
        g.db.close()
    '''






    @app.before_request
    def before_request():
        try :
            g.db = pymysql.connect(host=config_items['database']['dbhostname'], port=int(config_items['database']['dbport']), user=config_items['database']['dbusername'], passwd=config_items['database']['dbpassword'], db=config_items['database']['dbdb'],  autocommit=True )
            dbmessage = "Good, connected to " + config_items['database']['dbusername'] + "@" + config_items['database']['dbhostname'] + ":" + config_items['database']['dbport'] + "/" + config_items['database']['dbdb']
        except Exception as e :
            dbmessage = "Connection Failed connected to " + config_items['database']['dbusername'] + "@" + config_items['database']['dbhostname'] + ":" + config_items['database']['dbport'] + "/" + config_items['database']['dbdb'] + " With Error " + str(e)
            return dbmessage

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
            decoded_uname_pass = base64.b64decode(uname_pass_64).decode("utf-8")
            username = decoded_uname_pass.split(":")[0]


        except Exception as e :
            # No Basic Auth, either local access or IP whitelist
            username = "local_or_ip_whitelist"
            g.session_endorsements.append(("conntype","whitelist"))
            g.session_restrictions.append(("conntype","whitelist"))

        else:

            # Parsing was successful add ldap endorsment
            g.session_endorsements.append(("conntype","ldap"))
            g.session_restrictions.append(("conntype","ldap"))

        finally:
            g.USERNAME = username

        # Robot Authentication
        try:
            robot_header = ast.literal_eval(request.headers.get("robotauth", "False"))

            if robot_header == True :
                # I need to do robot auth
                username, apikey = auth_header.split(':')

                g.USERNAME = username


                auth_cursor = g.db.cursor(pymysql.cursors.DictCursor)

                '''
                Integrating Token Types. For now new tokens types will be processed
                here. In the future this "endorsements" section will be replaced
                with logic to look at our new centralized authorization system.
                '''

                anyvalid = False
                for tokentype in ["robot", "sapi", "ipintel"] :

                    key_valid = validate_key(username=username, giventoken=apikey, dbcur=auth_cursor, tokentype=tokentype)

                    print(tokentype, key_valid)

                    if key_valid == True :
                        # Add Robots Endorsement and Restriction
                        g.session_endorsements.append(("conntype",tokentype))
                        g.session_restrictions.append(("conntype",tokentype))
                        anyvalid = True
                        # No break loop
                        break
                if anyvalid == False :
                    # No Valid Token was found
                    abort(403)

                auth_cursor.close()

            else:
                # This isn't a robot call
                pass
        except AttributeError as e :
            abort(403)
        except SyntaxError as e:
            abort(500)
        finally:
            pass

        # Default Endorsement
        g.session_endorsements.append(("username","{}".format(g.USERNAME)))

        # DEFAULT Fresh. Use this instead of "Fresh" Values to allow for query caching.
        NOW = int(time.time())
        seconds_after_midnight = NOW % 86400
        MIDNIGHT = NOW - seconds_after_midnight
        oldest = MIDNIGHT - (86400*2)


        g.NOW = NOW
        g.MIDNIGHT = MIDNIGHT
        g.twoDayTimestamp = oldest
        g.cur = g.db.cursor(pymysql.cursors.DictCursor)
        g.HTTPENDPOINT = config_items["webserver"]["accesslink"]
        g.config_items = config_items

    @app.after_request
    def after_request(response) :
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

    ## API 2 Imports
    from jelly_api_2 import root
    from jelly_api_2 import sapi_listusers
    from jelly_api_2 import sapi_adduser
    from jelly_api_2 import sapi_addtoken
    from jelly_api_2 import hostsearch

    # Register API Blueprints for Version 2
    app.register_blueprint(root.root, url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(sapi_listusers.sapi_listusers, url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(sapi_adduser.sapi_adduser, url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(sapi_addtoken.sapi_addtoken, url_prefix=config_items["v2api"]["root"])
    app.register_blueprint(hostsearch.hostsearch, url_prefix=config_items["v2api"]["root"])

    @app.template_filter('ctime')
    def timectime(s):
        return time.ctime(s)

    @app.template_filter('firstx')
    def firstx(s,x):
        return s[:x]

    @app.route("/")
    def index():
        # Index
        return render_template("index.html")


    app.run(debug=FDEBUG, port=int(config_items['webserver']['port']) , threaded=True, host=config_items['webserver']['bindaddress'])



# Run if Execute from CLI
if __name__ == "__main__":
    ui(CONFIG, FDEBUG)
