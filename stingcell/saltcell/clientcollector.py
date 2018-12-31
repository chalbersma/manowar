#!/usr/bin/env python3

'''
A ClientSide Collector
'''

import socket
import time

import json

import ipaddress
import logging
import jq
import yaml

class Host:
    def __init__(self, minion_file="minion", base_config_file=False, local_cols=[False, None],
                 host_configs=False, ipintel_configs=False):

        self.logger = logging.getLogger("saltcell.clientcollector.Host")

        self.minion_file = minion_file

        self.salt_caller = self.start_minion()

        self.base_config_file = self.get_configs(base_config_file, local_cols)

        self.host_configs = host_configs

        self.logger.info("Read Information :\n{}".format(self.base_config_file))

        self.collection_info = self.getall_collections()

        self.basedata = self.getbasedata()

        self.ipintel_configs = ipintel_configs

        if self.ipintel_configs.get("dointel", False) is True:
            self.myipintel = self.ipintel()
        else:
            # Empty
            self.myipintel = list()

    def todict(self):

        return_dict = {"collection_data" : self.collection_info,
                       "ip_intel" : self.myipintel,
                       **self.basedata}

        return return_dict


    def get_configs(self, base_config_file, local_cols):

        if isinstance(base_config_file, dict):
            # I've been given the configuration
            to_collect_items = base_config_file
        elif isinstance(base_config_file, str):
            # I've been given a filename parse it
            with open(base_config_file, "r") as base_config_file:
                try:
                    to_collect_items = yaml.safe_load(base_config_file)
                except yaml.YAMLError as yaml_error:
                    self.logger.error("Unable to read collection configuration file {} with error : \n{}".format(base_config_file, str(yaml_error)))
                    to_collect_items = dict()

        if local_cols[0] is True:
            # Do Local Cols
            collection_d_dir = local_cols[1]
            collections_files = list()
            for (dirpath, dirnames, filenames) in os.walk(collections_d_dir) :
                for singlefile in filenames :
                    onefile = dirpath + "/" +  singlefile
                    #print(singlefile.find(".ini", -4))
                    if singlefile.find(".yaml", -4) > 0 :
                        # File ends with .ini Last 4 chars
                        collections_files.append(onefile)

            for collection_file in collections_files :
                try:
                    # Read Our INI with our data collection rules
                    this_local_coll = yaml.safe_load(collection_file)
                except Exception as e: # pylint: disable=broad-except, invalid-name
                    sys.stderr.write("Bad collection configuration file {} cannot parse: {}".format(collection_file, str(e)))
                else:
                    # I've read and parsed this file let's add the things
                    for this_new_coll_key in this_local_coll.get("collections", {}).keys():
                        to_collect_items["collections"][this_new_coll_key]=this_local_coll[this_new_coll_key]

        return to_collect_items

    def start_minion(self):

        # Any Earlier and I'll fubar the logger
        import salt.config
        import salt.client

        minion_opts = salt.config.minion_config(self.minion_file)

        salt_caller = salt.client.Caller(c_path=".", mopts=minion_opts)

        return salt_caller


    def getone(self, cname, collection):

        results_dictionary = dict()
        results_dictionary[cname] = dict()

        is_multi = collection.get("multi", False)

        if collection.get("salt", False) is True:

            this_find = self.salt_caller.function(collection["saltfactor"], \
                                            *collection["saltargs"], \
                                            **collection["saltkwargs"])

            if is_multi:
                # Multi so do the JQ bits
                parsed_result = jq.jq(collection["jq_parse"]).transform(this_find)

                results_dictionary[cname] = parsed_result
            else:
                # Not Multi the whole thing goes
                results_dictionary[cname]["default"] = str(this_find)

        else:
            results_dictionary = {"type" : {"subtype", "value"}}

        return results_dictionary

    def getall_collections(self):

        myresults = dict()

        for this_collection in self.base_config_file["collections"].keys():
            self.logger.info("Collection {} Processing".format(this_collection))

            this_result = self.getone(this_collection, self.base_config_file["collections"][this_collection])

            myresults[this_collection] = this_result[this_collection]

        myresults["host_host"] = self.gethostmeta()

        return myresults

    def gethostmeta(self):

        '''
        Takes the host metadata given and stores it puts defaults for nothing.
        '''

        hostmeta = dict()

        hostconfig=self.host_configs

        hostmeta["hostname"] = socket.gethostname()

        if hostconfig.get("pop", False) is not False:
            hostmeta["pop"] = str(hostconfig["pop"])
        else:
            hostmeta["pop"] = "none"

        if hostconfig.get("srvtype", False) is not False:
            hostmeta["srvtype"] = str(hostconfig["srvtype"])
        else:
            hostmeta["srvtype"] = "none"

        if hostconfig.get("status", False) is not False:
            hostmeta["status"] = str(hostconfig["status"])
        else:
            hostmeta["status"] = "none"

        if hostconfig.get("externalid", False) is not False:
            hostmeta["externalid"] = str(hostconfig["externalid"])

        self.logger.debug("Host Meta Information: {}".format(hostmeta))

        return hostmeta

    def getbasedata(self):

        '''
        Get the Basic Data like Collection Timestamp,
        A copy of the host data
        And any other meta data that shouldn't be stored as a collection
        '''

        basedata = self.gethostmeta()

        basedata["collection_timestamp"] = int(time.time())

        return basedata

    def ipintel(self):

        '''
        Get's IPs from the IPV6 and IPV4 collection

        Future work, make configuralbe parsing
        '''

        PRIVATE_NETWORKS = [ipaddress.ip_network("127.0.0.0/8"),
                            ipaddress.ip_network("10.0.0.0/8"),
                            ipaddress.ip_network("172.16.0.0/12"),
                            ipaddress.ip_network("192.168.0.0/16"),
                            ipaddress.ip_network("fd00::/8")]

        found_intel = list()

        # Get Local Addresses
        ipa_object = list()
        ipa_object.extend(list(self.collection_info["ipv4_addr"].keys()))
        ipa_object.extend(list(self.collection_info["ipv6_addr"].keys()))


        self.logger.info("Raw Intel Object for this Host : \n{}".format(ipa_object))

        ipv4 = list()
        ipv6 = list()

        for this_unvalidated_ip in ipa_object :

            self.logger.info("Doing the needful for IP : \n{}".format(this_unvalidated_ip))

            isipv4=False
            isipv6=False

            try:
                validated_ipv4 = socket.inet_pton(socket.AF_INET, this_unvalidated_ip)
                isipv4 = True
            except OSError :
                # IPV4 Validation Failed, Try IPV6
                try:
                    validated_ipv6 = socket.inet_pton(socket.AF_INET6, this_unvalidated_ip)
                    isipv6 = True
                except OSError :
                    pass
            finally:
                # After this checks let's see what showed up
                if isipv4 or isipv6 :
                    # On or the other was true let's see if it's a private address
                    this_ip = ipaddress.ip_address(this_unvalidated_ip)

                    is_private = False
                    for priv_net in PRIVATE_NETWORKS :
                        if this_ip in priv_net :
                            # This is a private ip
                            self.logger.debug("{} is in Private network {}".format(this_ip, priv_net))
                            is_private = True
                            break
                        else :
                            # Check the other Private Networks
                            continue

                    if is_private == False :
                        # It's not a private IP so add it to the intel report
                        if isipv4 :
                            ipv4.append(this_unvalidated_ip)
                        elif isipv6 :
                            ipv6.append(this_unvalidated_ip)

        unduped_ipv4 = list(set(ipv4))
        unduped_ipv6 = list(set(ipv6))

        this_intel = dict()
        this_intel["host4"] = unduped_ipv4
        this_intel["host6"] = unduped_ipv6

        for thing in ["host4", "host6"] :
            for ip in this_intel[thing] :
                this_report = { "iptype" : thing , \
                                 "ip" : ip }

                found_intel.append(this_report)

        return found_intel
