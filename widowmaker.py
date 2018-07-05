#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

Publish side of the house (maybe)
Read the servers4.csv file and publish the info to the rabbitmq server.
'''

import pika, os
import argparse
import jreadconfig
import time
import random
import csv
import multiprocessing
import logging

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

    LOGGER = logging.getLogger("widowmaker.py")

    # Make sure my included projects properly log.
    logging.getLogger("pika").setLevel(logging.WARNING)
    logging.getLogger("paramiko").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


class yeehaw() :

    def __init__(self, config_dict=False, logger=False) :

        # Parse CLODUAMQP_URL (fallback to localhost)
        self.logger = logger

        self.config_dict = config_dict
        self.url = "amqp://{}:{}@{}/".format( config_dict["queue"].get("qpass", "guest"), \
                                        config_dict["queue"].get("qpass", "guest"), \
                                        config_dict["queue"].get("qhost", "localhost") )

        self.queue_name = config_dict["queue"].get("queue_name", "waiting_hosts")

        # Make a Connection
        self.params = pika.URLParameters(self.url)

        self.params.socket_timeout = config_dict["queue"].get("queue_timeout", 5)

        self.connection = pika.BlockingConnection(self.params) # Connect to CloudAMQP

        self.channel = self.connection.channel() # start a channel

        self.channel.queue_declare(queue=self.queue_name) # Declare a queue

        self.edgecast_csv = config_dict["queue"].get("csv_file", "/oc/local/netinfo/etc/servers4.csv")

        self.logger.info("Using file {} to find and add CSV files.".format(str(self.edgecast_csv)))

        self.edgecast_hosts = self.read_hosts()

        self.logger.info("Adding {} hosts to the queue.".format(str(len(self.edgecast_hosts))))

    # send a message

    def send_all_hosts(self) :

        for host in self.edgecast_hosts :
            self.send_host( the_tuple = tuple(host) )


    def send_host(self, the_tuple=("hostname", "srvtype", "pop", "status") ):

        self.channel.basic_publish(exchange='', routing_key=self.queue_name, body=str(the_tuple))

    def read_hosts(self) :

        csvfile_object = open(self.edgecast_csv, 'r')
        hosts = csv.reader(csvfile_object)
        priority_hosts = list()
        secondary_hosts = list()
        for host in hosts:
            if host[3] == "prod":
                priority_hosts.append(host)
            else:
                secondary_hosts.append(host)

        # Shuffle My Priority Hosts so that
        random.shuffle(priority_hosts)

        # Make me try the shuffled prod hosts before the rest
        return_hosts = priority_hosts + secondary_hosts

        return return_hosts

    def __del__(self) :

        # Close my Queue Connection
        self.connection.close()

if __name__ == "__main__" :

    LOGGER.info("Welcome to Widowmaker")

    hosts = yeehaw(config_dict=CONFIG, logger=LOGGER)

    hosts.send_all_hosts()
