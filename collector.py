#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

### Collector

The collector is designed to grab data back for one host. The first and
current collector utilizes paramiko/ssh to log onto it's host, run a series
of commands configured in `collector.ini` (and stored in SVN). If ran by
hand you can utilize com3mand line flags to test the data being given by
a particular host. The collector will return a json or python dictionary
that meets the standards specified in `jellyfish_storage.json.schema`
(also stored in SVN). You can utilize the StorageJSONVerify module to
confirm the goodness (or badness) of a particular set of data.

'''

import argparse
from time import time
from time import sleep

import json
from configparser import ConfigParser
import paramiko
from select import select
import socket
import sys
# Subprocess is needed here
import subprocess # nosec

from process_ip_intel import process_ip_intel

## To work nicely with PIPes
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # Generally Going to Be /oc/local/netinfo/etc/servers4.csv
    parser.add_argument("-t", "--target", help="Host to Target.", required=True)
    parser.add_argument("-c", "--config", help="Collector Config File", required=True)
    parser.add_argument("-u", "--username", help="SSH Username", required=True)
    parser.add_argument("-k", "--keyfile", help="SSH Key to use", required=True)
    parser.add_argument("-4", "--ipv4", help="Use IPV4 instead of default", action='store_true')
    parser.add_argument("-6", "--ipv6", help="Use IPV4 instead of default", action='store_true')
    parser.add_argument("-a", "--appendedgecast", help="add FQDN to host", action='store_true')
    parser.add_argument("-p", "--pop", help="POP of Server")
    parser.add_argument("-s", "--srvtype", help="SRVType of Server")
    parser.add_argument("-m", "--status", help="Status of the Server")
    parser.add_argument("-i", "--uberid", help="Uber ID of Server")
    parser._optionals.title = "DESCRIPTION "

    # Parser Args
    args = parser.parse_args()

    # Grab Variables
    HOST = args.target
    CONFIG = args.config
    USERNAME = args.username
    KEYFILE = args.keyfile

    if args.pop is not None:
        # If we recieved a POP
        POP = args.pop
    else:
        # If we Didn't
        POP = "N/A"

    if args.srvtype is not None:
        # If we recieved a SRVTYPE
        SRVTYPE = args.srvtype
    else:
        SRVTYPE = "N/A"

    if args.uberid is not None:
        UBERID = args.uberid
    else:
        UBERID = "N/A"

    if args.status is not None:
        STATUS = args.status
    else:
        STATUS = "N/A"

    # Set paramiko_host

def collector(HOST, CONFIG, USERNAME, KEYFILE, POP, SRVTYPE, UBERID, STATUS, IPV4, IPV6, APPEND):

    '''
    Main Function for Collector. Calling this with the right variable should allow you to utilize
    this functionality in a non-interactive method
    '''

    # Timestamp to use for this collection time.
    COLLECTION_TIME = int(time())

    items_collected = dict()
    items_collected["collection_timestamp"] = COLLECTION_TIME
    items_collected["collection_hostname"] = HOST
    items_collected["srvtype"] = SRVTYPE
    items_collected["pop"] = POP
    items_collected["uber_id"] = UBERID
    items_collected["status"] = STATUS
    items_collected["ip_intel"] = list()

    # See if we want to do the Edgecast Specific append
    if APPEND:
        rawish_hostname = '{}.edgecastcdn.net'.format(HOST)
    else:
        rawish_hostname = HOST

    # So I'm going to search for both ipv4 & ipv6 addresses. And then add the intel
    # This is for IP Intelligence.

    ipv4_addr = False
    ipv6_addr = False

    try:
        ipv4_addr = socket.gethostbyname_ex(rawish_hostname)[2][0]
    except Exception as e:
        items_collected["ipv4_note"] = "Failed Finding IPV4 Address" + str(e)
    else:
        # Add IP Found to IP Intel
        # Validate this is really an IPV4 address
        try:
            validated_ipv4 = socket.inet_pton(socket.AF_INET, ipv4_addr)
        except OSError as oserr:
            # No IPV4 Address
            items_collected["ipv4_val_error"] = "Found IPV4 Address would not Validate" + str(oserr)
        else :
            # It's true record the intel
            items_collected["ip_intel"].append({ "iptype":"host4", \
                                        "ip":ipv4_addr })

    try:
        ipv6_addr = socket.getaddrinfo(rawish_hostname, None)[3][4][0]
    except Exception as e:
        items_collected["ipv6_note"] = "Failed Finding IPV6 Address" + str(e)
    else:
        try:
            validated_ipv6 = socket.inet_pton(socket.AF_INET6, ipv6_addr)
        except OSError as oserr:
            # No IPV6 Address
            items_collected["ipv6_val_error"] = "Found IPV6 Address would not Validate" + str(oserr)
        else :
            items_collected["ip_intel"].append({ "iptype":"host6", \
                                        "ip":ipv6_addr })

    if IPV4 :
        if ipv4_addr == False :
            items_collected["true_failure"] = True
            items_collected["collection_status"] = "Failed Finding IPV4 Address"
            if __name__ == "__main__":
                json_string = json.dumps(items_collected, sort_keys=True, indent=4)
                print(json_string)
                sys.exit(1)
            # Stop the Loop
            return items_collected
        paramiko_host = ipv4_addr
    elif IPV6 :
        if ipv6_addr == False :
            items_collected["true_failure"] = True
            items_collected["collection_status"] = "Failed Finding IPV6 Address"
            if __name__ == "__main__":
                json_string = json.dumps(items_collected, sort_keys=True, indent=4)
                print(json_string)
                sys.exit(1)
            # Stop the Loop
            return items_collected
        paramiko_host = ipv6_addr

    else:
        # Don't do shit just return the rawish_hostname
        paramiko_host = rawish_hostname

    try:
        # Read Our INI with our data collection rules
        config = ConfigParser()
        config.read(CONFIG)

    except Exception as e: # pylint: disable=broad-except, invalid-name
        items_collected["config_parsing"] = "Failed to Parse Config"+CONFIG
        items_collected["config_parsing_error"] = str(e)
        items_collected["true_failure"] = True
        if __name__ == "__main__":
            print(json.dumps(items_collected, sort_keys=True, indent=4))
            sys.exit('Bad configuration file {}'.format(e))

        return items_collected

    # Grab me Collections Items Turn them into a Dictionary
    collection_items = dict()

    # Collection Items
    for section in config:
        if section != "DEFAULT" and section != "GLOBAL":
            # Ignore the Default and Global Stuff
            collection_items[section] = {"multi" : config[section]["multi"],
                                         "collection" : config[section]["collection"]}


    # Dict for my collected Items

    items_collected["connection_string"] = str(USERNAME) + str("@") + paramiko_host
    items_collected["collection_data"] = {}


    items_collected["collection_status"] = "UNKNOWN"
    # Setup our Policy
    try:
        ssh_connection = paramiko.SSHClient()
        ssh_connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    except Exception as e:
        print("Error setting up paramiko: ", str(e))
    else:
        # Try Connecting
        try:
            ssh_connection.connect(paramiko_host, timeout=2, \
                            username=USERNAME, key_filename=KEYFILE)
            transport = ssh_connection.get_transport()
            items_collected["collection_status"] = "SSH SUCCESS"
        except paramiko.AuthenticationException as error:
            # Exit if we auth bad
            items_collected["collection_status"] = "SSH AUTH ERROR"
            items_collected["paramiko_error"] = str(error)
            items_collected["true_failure"] = True
            if __name__ == "__main__":
                print(json.dumps(items_collected, sort_keys=True, indent=4))

            try:
                ssh_connection.close()
            except Exception as e: # pylint: disable=broad-except, invalid-name
                items_collected["paramiko_secondary_error"] = str(e)

            return items_collected

            sys.exit(1)

        except socket.timeout as error:
            # Exit if we timeout
            items_collected["collection_status"] = "SSH TIMEOUT"
            items_collected["paramiko_error"] = str(error)
            items_collected["true_failure"] = True

            try:
                ssh_connection.close()
            except Exception as e: # pylint: disable=broad-except, invalid-name
                items_collected["paramiko_secondary_error"] = str(e)

            if __name__ == "__main__":
                print(json.dumps(items_collected, sort_keys=True, indent=4))
                sys.exit(1)

            return items_collected

        except FileNotFoundError as error:
            items_collected["collection_status"] = "SSH CANNOT FIND KEYFILE"+KEYFILE
            items_collected["paramiko_error"] = str(error)
            items_collected["true_failure"] = True

            try:
                ssh_connection.close()
            except Exception as e: # pylint: disable=broad-except, invalid-name
                items_collected["paramiko_secondary_error"] = str(e)

            if __name__ == "__main__":
                print(json.dumps(items_collected, sort_keys=True, indent=4))
                sys.exit(1)

            return items_collected

        except Exception as mainerror:
            # Exit for other errors
            items_collected["collection_status"] = "SSH GENERIC FAILURE"
            items_collected["paramiko_error"] = str(mainerror)
            items_collected["true_failure"] = True

            try:
                ssh_connection.close()
            except Exception as e:
                items_collected["paramiko_secondary_error"] = str(e)

            if __name__ == "__main__":
                print(json.dumps(items_collected, sort_keys=True, indent=4))
                sys.exit(1)

            return items_collected

    ## Issue Command Function
    ## Shamelessly Yanked from https://goo.gl/3zJvMN
    def issue_command(transport, pause, command):
        #print("COMMAND TO RUN: ", command)
        try:
            # The good news is that bandit is catching this. The idea here is to
            # Run a command on the host. This is the core of Jellyfish's "get"
            # functionality.
            chan = transport.open_session()
            chan.exec_command(command) # nosec
        except Exception as e:
            print("Attempting to Open Transport Session Failed: ", str(e))
            stdout = ""
            stderr = "Attempting to Open Transport Session Failed: " + str(e)
            exit_status = 999
        else:
            # Some Basic Stuff
            buff_size = 1024
            stdout = ""
            stderr = ""
            try:
                while not chan.exit_status_ready():
                    sleep(pause)
                    if chan.recv_ready():
                        stdout += chan.recv(buff_size).decode('utf-8')

                    if chan.recv_stderr_ready():
                        stderr += chan.recv_stderr(buff_size).decode('utf-8')

                exit_status = chan.recv_exit_status()
                # Need to gobble up any remaining output after program terminates...
                while chan.recv_ready():
                    stdout += chan.recv(buff_size).decode('utf-8')

                while chan.recv_stderr_ready():
                    stderr += chan.recv_stderr(buff_size).decode('utf-8')
            except Exception as e:
                print("Error when Getting output from Command: ", str(e))
                stdout = ""
                stderr = "Error when Getting output from Command: "
                exit_status = 998
            finally:
                pass
        finally:
            pass

        return exit_status, stdout, stderr

    for collection_category in collection_items:

        # For this collection connect and run our command
        exit_status, stdout, stderr = issue_command(transport, 1, \
                                    collection_items[collection_category]["collection"])

        #print(type(stdout))
        #print(type(exit_status))
        #print("EXIT_STATUS", exit_status)
        #print("STDOUT", stdout)
        #print("STDERR", stderr)
        # DEBUG
        '''
        if collection_category in ["services"]:
            print(collection_category)
            print(exit_status, "\n" )
            print(stdout, "\n")
            print(stderr, "\n")
            print(collection_items[collection_category]["collection"])
        '''
        #else:
            #print(collection_category)


        # Create a new parsed_data empty dictionary
        parsed_data = dict()

        # Error Condition
        #print(exit_status, stderr)
        if exit_status > 0 or stdout == "":
            exit_status, stdout, stderr = issue_command(transport, 1, \
                                          collection_items[collection_category]["collection"])

            if exit_status > 0 or stdout == "":
                exit_status, stdout, stderr = issue_command(transport, 1, \
                                              collection_items[collection_category]["collection"])

        # If three tries fails
        if exit_status > 0 or stdout == "":

            error_dict = {"collection_failed" : str("Collection of " + str(collection_category) +\
                        "Failed with response: " + str(exit_status) + " : " + str(stdout))}

            parsed_data = error_dict
        # Multi Dimensional Data
        elif collection_items[collection_category]["multi"] == "TRUE":
            #Debug raw_output[1]
            # Debug
            multiD_dict = dict()
            for item in stdout.splitlines():
                #print(item)
                multiD_dict[item.split()[0]] = " ".join(item.split()[1:])
                parsed_data = multiD_dict
        # Collection and Split if you're not a multi Dim
        else:
            collected_data = {"default" : stdout.strip()}
            #print(collected_data)
            parsed_data = collected_data

        # Add you're data to the return data
        items_collected["collection_data"][collection_category] = parsed_data
        # Close SSH_Connection
        #ssh_connection.flush()

    # Close My Connection
    ssh_connection.close()

    # Add the Host Items to the Collection for Easy Bucketing
    host_host = dict()

    host_host["POP"] = POP
    host_host["SRVTYPE"] = SRVTYPE
    host_host["UBERID"] = UBERID
    host_host["STATUS"] = STATUS
    host_host["HOSTNAME"] = HOST

    items_collected["collection_data"]["host_host"] = host_host

    # Search for IP Intelligence
    for viptype in ["vips4", "vips6"] :
        if viptype in items_collected["collection_data"].keys() and len(items_collected["collection_data"][viptype]) > 0 :
            for thisvip in items_collected["collection_data"][viptype].keys() :
                if items_collected["collection_data"][viptype][thisvip] == "ACTIVE" :
                    # Active VIP
                    items_collected["ip_intel"].append({"iptype":viptype, \
                                                "ip":thisvip })
                else :
                    # Not actually needed Pass
                    pass


    #print(json.dumps(items_collected)) On CLI Run
    if __name__ == "__main__":
        print(json.dumps(items_collected, sort_keys=True, indent=4))

    # Return (Ignored on CLI Run)
    return items_collected

if __name__ == "__main__":
    collector(HOST, CONFIG, USERNAME, KEYFILE, POP, SRVTYPE, \
              UBERID, STATUS, args.ipv4, args.ipv6, args.appendedgecast)
