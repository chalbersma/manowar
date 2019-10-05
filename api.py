#!/usr/bin/env python3

'''
Flask Application that is the API for:

- Storing Data
'''


import sys
import logging
import argparse
import os
import os.path

import pymysql
import flask
import yaml

def flask_init(**kwargs):

    '''
    Initializes my Flask API.
    '''

    logger = logging.getLogger("flask_init:api.py")

    logger.critical("Initializing Flask.")

    logger.debug("Args : {}".format(kwargs))

    initialization_okay = True
    app = None

    if kwargs.get("configs", False) is False:
        logger.error("No Configurations. Exiting.")
        initialization_okay = False

    if isinstance(kwargs["configs"].get("database", False), dict):
        dbconfigs = kwargs["configs"].get("database", {})
        logger.debug("DB Configs : {}".format(dbconfigs))

        # Start Flask Server
        app = flask.Flask(__name__)


        try:
            # TODO allow SSL Conns

            sslca_opts = dict()
            if dbconfigs.get("sslca", False) is not False:
                if os.path.exists(dbconfigs["sslca"]) is True:
                    sslca_opts["ssl"] = {"ca" : dbconfigs("sslca")}
                else:
                    logger.error("Databaase SSL CA Cert {} non-existent.".format(dbconfigs["sslca"]))
            else:
                logger.warning("Database doesn't have SSL CA Certificate Specified SSL not in Use. This can be dangerous.")


            with app.app_context():
                flask.g.db = pymysql.connect(host=dbconfigs.get("host", "localhost"),
                                                port=int(dbconfigs.get('port', 3306)),
                                                user=dbconfigs['user'],
                                                passwd=dbconfigs['pass'],
                                                db=dbconfigs.get("db", "manowar"),
                                                autocommit=True,
                                                **sslca_opts)

                logger.info("Good, connected to {}@{}:{}/{}".format(dbconfigs['user'],
                                                                    dbconfigs.get("host", "localhost"),
                                                                    int(dbconfigs.get('port', 3306)),
                                                                    dbconfigs.get("db", "manowar")))

        except Exception as dbconn_error:
            logger.error("Connection Failed connected to {}@{}:{}/{} With Error {}".format(dbconfigs.get("user", "unknown"),
                                                                                           dbconfigs.get("host", "localhost"),
                                                                                           int(dbconfigs.get('port', 3306)),
                                                                                           dbconfigs.get("db", "manowar"),
                                                                                           str(dbconn_error)))

        else:


            @app.route("/")
            def hello_world():
                return "Heyo"

            initialization_okay = True


    else:
        logger.error("No Database Configurations Given")
        initialization_okay = False


    if initialization_okay:
        start_good = True
    else:
        start_good = False


    return start_good, app


if __name__ == "__main__":

    PARSER = argparse.ArgumentParser()

    PARSER.add_argument("-c", "--configfile", help="Config File for Scheduler", required=True)
    PARSER.add_argument("-d", "--flaskdebug", action='store_true', help="Turn on Flask Debugging")
    PARSER.add_argument("-v", "--verbose", action='append_const', help="Turn on Verbosity", const=1, default=[])

    ARGS = PARSER.parse_args()

    FDEBUG = ARGS.flaskdebug
    CONFIG = ARGS.configfile

    VERBOSE = len(ARGS.verbose)

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

    exit_code = 255

    try:
        LOGGER.debug("Loading Configuration file from : {}".format(CONFIG))
        with open(CONFIG, "r") as yaml_config_file:
            MOW_CONFIGS = yaml.safe_load(yaml_config_file)
        LOGGER.debug("MOW CONFIGS : {}".format(MOW_CONFIGS))
    except Exception as yaml_read_error:
        LOGGER.error("Unable to Read Configs at {}. Exiting.".format(str(yaml_read_error)))
        exit_code = 1
    else:
        LOGGER.info("Starting Up Flask Service....")

        instance_config = {"configs" : MOW_CONFIGS,
                           "flask_debug" : FDEBUG,
                           "verbose" : VERBOSE}

        try:
            good, flaskapp = flask_init(**instance_config)
        except Exception as runtime_error:
            LOGGER.error("Error when running webserver with : {}".format(runtime_error))
        else:
            if good is True:

                exit_code = 0
                init_args = {"port" : MOW_CONFIGS["flask"].get("port", 5000),
                             "host" : MOW_CONFIGS["flask"].get("listen", "127.0.0.1"),
                             "debug" : MOW_CONFIGS["flask"].get("debug", False)}

                if ARGS.debug is True:
                    LOGGER.info("In Debug")
                    init_args["debug"] = True

                LOGGER.info("Initializing Server {}".format(init))
                flaskapp.run()
            else:
                LOGGER.info("Exit Code Listed as False")
                exit_code = 1
    finally:
        LOGGER.debug("Exit Code: {}".format(exit_code))
        sys.exit(exit_code)

    sys.exit(3)
