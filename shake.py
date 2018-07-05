#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# example_consumer.py
import pika, os, time
import jreadconfig
import argparse
import ast
import multiprocessing
import json
import requests
import logging
import signal
from functools import partial

from collector import collector

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", help="JSON Config File with our Storage Info", required=True)
    parser.add_argument("-V", "--verbose", action="store_true", help="Enable Verbose Mode")
    parser._optionals.title = "DESCRIPTION "

    # Parser Args
    args = parser.parse_args()

    # Grab Variables
    CONFIG=jreadconfig.jreadconfig(args.config)

    VERBOSE=args.verbose
    FORMAT="%(levelname)s %(asctime)s %(name)s : %(message)s"

    if VERBOSE == True :
        # Set Loglevel
        logging.basicConfig(level=logging.DEBUG,
                            format=FORMAT)
    else :
        logging.basicConfig(level=logging.ERROR,
                            format=FORMAT)

    LOGGER = logging.getLogger("shake.py")

    # Make sure my included projects properly log.
    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

class lasso():

    def __init__(self, config_dict={}, my_name="unnammed", logger=False) :
        # Parse CLODUAMQP_URL (fallback to localhost)

        self.logger = logger
        self.my_name = my_name
        self.config_dict = config_dict
        self.url = "amqp://{}:{}@{}/".format( config_dict["queue"].get("qpass", "guest"), \
                                        config_dict["queue"].get("qpass", "guest"), \
                                        config_dict["queue"].get("qhost", "localhost") )

        self.queue_name = config_dict["queue"].get("queue_name", "waiting_hosts")

        # Make a Connection
        self.params = pika.URLParameters(self.url)

        self.params.socket_timeout = config_dict["queue"].get("queue_timeout", 5)

        self.connection = pika.BlockingConnection(self.params)

        self.channel = self.connection.channel()

        self.channel.queue_declare(queue=self.queue_name)

        self.channel.basic_consume(self.callback, queue=self.queue_name, \
                no_ack=True)

        # start consuming (blocks)

        self.logger.debug("Thread {} -> Connected to Queue beginning Consuming".format(str(self.my_name)))

    def start_consuming_hosts(self) :

        # Put this outside of the main function so the object can be initialized
        # Cleanly

        try:
            self.channel.start_consuming()
        except KeyboardInterrupt as keyboarderror :
            # i'm okay if I control C
            pass
        except OSError as oserror :
            # This is also okay, this happens sometimes when killing threads
            pass


    def __del__(self) :
        self.logger.debug("Thread {} -> Closing Connection to Queue".format(str(self.my_name)))
        self.channel.stop_consuming()
        self.connection.close()

    def process_host_from_line(self, body=False):
        host_tuple = ast.literal_eval(body.decode())

        this_result = self.collect_host(host_tuple)

        if body != False :
            hostname = str(host_tuple[0])
        else:
            hostname = str(body)

        if "true_failure" not in this_result.keys() :
            # We're good store it
            self.logger.debug("Thread {} -> Collection for host {} successful. Attempting Storage.".format(str(self.my_name), str(hostname)))
            self.send_results(hosttuple=host_tuple, results_dict=this_result)
            pass
        else :
            # We aien't good get outta here
            self.logger.warning("Thread {} -> Collection for host {} unsuccessful. Not attempting Storage".format(str(self.my_name), str(hostname)))
            pass

    def send_results(self, hosttuple=False, results_dict={}):

        header_dict = { "Authorization" : \
                            "{}:{}".format(self.config_dict["sapi"].get("sapi_username","nobody"), \
                                          self.config_dict["sapi"].get("sapi_token","nothing")) ,\
                        "Content-Type" : "application/json" }

        base_url = self.config_dict["sapi"].get("sapi_endpoint","https://sapi.jellyfish.edgecast.com")
        send_url = "{}/sapi/puthostjson/".format(base_url)

        results_json = json.dumps(results_dict)

        if hosttuple != False :
            hostname = str(hosttuple[0])
        else:
            hostname = "Unknown"

        # Try this Upload
        try:
            this_request = requests.post(send_url, data=results_json, headers=header_dict)
            self.logger.debug("Thread {} -> Storing results for host : {} ".format(str(self.my_name), hostname))
        except Exception as e :
            # Do some error thing here.
            self.logger.error("Thread {} -> Storing results failed for host : {} with error {} ".format(str(self.my_name), hostname, str(e)))
            pass
        else :
            response_code = this_request.status_code

            if response_code == 200 :
                # Things Worked
                pass
                self.logger.info("Thread {} -> Storing results completed successfully for host : {}".format(str(self.my_name), hostname))
            else :
                # Things Failed retry
                pass
                self.logger.warning("Thread {} -> Storing results failed for host : {} with HTTP error code of {}".format(str(self.my_name), hostname, str(response_code)))
                if response_code == 403 :
                    # Add additional error message noting that token may be wrong.
                    self.logger.warning("Thread {} -> Token may be incorrect for user {}. Please investigate configuration.".format(str(self.my_name), self.config_dict["sapi"].get("sapi_username","nobody")))

    def callback(self, ch, method, properties, body):
        self.logger.debug("Thread {} -> Pulled line off of queue : {}".format(str(self.my_name), str(body)))
        self.process_host_from_line(body)

    def collect_host(self, host_tuple):

        hostname = host_tuple[0]
        srvtype  = host_tuple[1]
        pop      = host_tuple[2]
        status   = host_tuple[3]

        # Uber ID's not implemented Yet
        uberid = "N/A"

        collector_config_file = self.config_dict["paramiko"].get("collector_config", \
                                                                "/oc/local/secops/jellyfish2/etc/shake.ini")

        username = self.config_dict["paramiko"].get("paramiko_user", \
                                                                "manager")

        keyfile = self.config_dict["paramiko"].get("paramiko_key", \
                                                   "/var/jellyfish/.ssh/id_rsa")

        ipv4 = self.config_dict["paramiko"].get("ipv4", True)
        ipv6 = self.config_dict["paramiko"].get("ipv6", False)

        do_ec_append = self.config_dict["paramiko"].get("edgecast_append", True)

        this_host_collection_result = collector(hostname, collector_config_file, \
                                                username, keyfile, pop, srvtype, \
                                                uberid, status, ipv4, ipv6, do_ec_append)

        self.logger.info("Thread {} -> Collection Attempt completed for host : {}".format(str(self.my_name), hostname))

        return this_host_collection_result




def create_lasso(config_dict=False, count=False, logger=False) :

    logger.debug("Thread {} -> instantiated".format(str(count)))

    # Initialize Object
    this_obj = lasso(config_dict=config_dict, my_name=count, logger=logger)

    # Setup Signal
    signal.signal(signal.SIGINT, partial(handle_signal, this_obj, logger))

    # Start consuming hosts from the Queue
    this_obj.start_consuming_hosts()

def handle_signal(this_lasso_obj, logger, signal, stack ):

    logger.debug("Thread {} -> recieved signal {}. Ending Thread.".format(str(this_lasso_obj.my_name), str(signal)))

    this_lasso_obj.__del__()


def spin_up_threads(config_dict={}, logger=False) :

    manager = multiprocessing.Manager()

    THREADS = config_dict["threads"].get("max", 16)

    logger.debug("Creating Pool of {} threads.".format(str(THREADS)))

    thread_dict = dict()

    for thread_count in range(0, THREADS) :

        thread_dict[thread_count] = multiprocessing.Process(target=create_lasso, \
                                    args=(config_dict, thread_count, logger) )

        thread_dict[thread_count].daemon = True
        thread_dict[thread_count].start()

    # Check if Failure


    while True :

        have_failures = False

        for thread in thread_dict.keys() :

            if thread_dict[thread].is_alive() == False :
                have_failures = True

        if have_failures == False :
            # No Failures Sleep and Try again
            try:
                time.sleep(30)
            except KeyboardInterrupt as error :
                # It's okay if I ctrl c
                break

        else :
            # Stuff has Ended, end loop
            logger.critical("One of my child threads has crashed. Ending program.")
            break

if __name__ == "__main__":

    # Boom shaka laka
    #this_runner = lasso(config_dict=CONFIG)

    LOGGER.info("Welcome to Shake")

    spin_up_threads(config_dict=CONFIG, logger=LOGGER)
