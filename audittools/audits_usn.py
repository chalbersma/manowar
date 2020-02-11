#!/usr/bin/env python3

'''
audits_usn.py

Given a Single USN let's create an manowar audit that represents that.
'''

import argparse
import json
import logging
import os
import os.path
import time
import re
import tempfile

import requests

if __name__ == "__main__":
    from audit_source import AuditSource
    from ubuntu_cve import mowCVEUbuntu
else:
    from audittools.audit_source import AuditSource
    from audittools.ubuntu_cve import mowCVEUbuntu



if __name__ == "__main__" :
    parser = argparse.ArgumentParser()
    #parser.add_argument("-v", "--verbose", action='store_true', help="Turn on Verbosity")
    parser.add_argument("-v", "--verbose", action='append_const', help="Turn on Verbosity", const=1, default=[])
    parser.add_argument("--nocache", action="store_true", help="Don't use local usn_db.json")
    parser.add_argument("--cacheage", default=21600, help="How long (in seconds) to accept local usn_db.json file default 6 hours 21600 seconds")
    parser.add_argument("--cachefile", default=None, help="Use this if you want to cache the db.json between runs")
    parser.add_argument("-o", "--output", default=False, help="File to output to")
    parser.add_argument("-p", "--print", action="store_true", help="Print Audit to Screen")
    parser.add_argument("-u", "--usn", required=True)

    args = parser.parse_args()

    VERBOSE = len(args.verbose)

    if VERBOSE == 0:
        logging.basicConfig(level=logging.ERROR)
    elif VERBOSE == 1:
        logging.basicConfig(level=logging.WARNING)
    elif VERBOSE == 2:
        logging.basicConfig(level=logging.INFO)
    else:
        logging.basicConfig(level=logging.DEBUG)

    USN = args.usn

    CACHEAGE = args.cacheage
    CACHEFILE = args.cachefile

    LOGGER = logging.getLogger("audits_usn.py")

    LOGGER.debug("Welcome to Audits USN.")

class AuditSourceUSN(AuditSource):

    '''
    Implements a Public AuditSource object for Ubuntu Security Notices
    '''

    __usn_regex = "[Uu][Ss][Nn]-\d{4}-\d{1}"
    __usn_url = "https://usn.ubuntu.com/usn-db/database.json"

    __default_cachefile = None
    __default_cacheage = 21600

    def __init__(self, **kwargs):

        # Run My Parent Init Function
        AuditSource.__init__(self, **kwargs)

        self.cachefile = kwargs.get("cachefile", self.__default_cachefile)
        self.cacheage = kwargs.get("cacheage", self.__default_cacheage)
        self.cachedata = None

        # Confirm I have a USN
        if re.match(self.__usn_regex, self.source_key) is None:
            raise ValueError("Source Key Doesn't look like a USN {}".format(str(self.source_key)))

        # Update My Cache
        if kwargs.get("ignore_cache", False) is False:
            self.handle_local_cache()

        self.usn_data = self.get_usn_data()

        self.populate_audit()

    def populate_audit(self):

        '''
        Assuming I have my USN Data as a Dictionary, Let's populate the self.audit_data & self.audit_name items from my
        parent function.
        '''

        self.audit_name = self.source_key.upper()

        self.audit_data = {**self.audit_data,
                           "vuln-name" : self.audit_name,
                           "vuln-primary-link" : self.usn_data["primary_link"],
                           "vuln-additional-links" : self.usn_data["reference_links"],
                           "vuln-short-description" : self.usn_data["isummary"],
                           "vuln-priority" : self.usn_data["highest_priority"],
                           "auditts" : int(self.usn_data["timestamp"])}

        # Caluclate Priority "vuln-priority" : kwargs.get("vuln-priority", None),
        self.audit_data["filters"], self.audit_data["comparisons"] = self.cal_bucket_defs()

        # Calulate Filters & Comparisons
        self.audit_data["vuln-long-description"] = "{}\n\nTLDR: {}\n".format(self.usn_data["description"], self.usn_data["action"])


    def get_usn_data(self):

        '''
        Turn the USN to an Audit Dictionary of type {"usn-number" : <data...>}
        '''

        if self.source_key is None:
            raise ValueError("Unknown USN")

        usn_num = "-".join(self.source_key.split("-")[1:])

        if self.cachedata is None:
            with open(self.cachefile) as cachefile_obj:
                try:
                    all_data = json.load(cachefile_obj)
                except Exception as json_fomat_error:
                    self.logger.error("JSON Formatting Error, Try removing Cache file.")
        else:
            self.logger.debug("Cachedata not loaded from file, already have in memory.")
            all_data = self.cachedata

        try:
            usn_data = all_data[usn_num]

            self.logger.debug("Loaded Data for USN {}".format(self.source_key))

        except Exception as read_json_error:
            self.logger.error("Unable to Find/Load USN {}.".format(self.source_key))
            self.logger.debug("Error Found when loading {} : {}".format(self.source_key, read_json_error))
            self.logger.debug("USN Num : {}".format(usn_num))

            usn_data = None
        else:
            self.logger.debug("Found Upstream USN Data for the following releases: {}".format(usn_data["releases"].keys()))

            # Parse CVEs
            usn_data["parsed_cves"] = list()
            usn_data["usn_num"] = usn_num
            usn_data["primary_link"] = "https://usn.ubuntu.com/{}/".format(usn_num)
            usn_data["reference_links"] = {self.source_key.upper() : usn_data["primary_link"]}

            highest_priority = 1

            for cve_string in usn_data["cves"]:
                try:
                    this_cve_obj = mowCVEUbuntu(cve=cve_string)
                except ValueError as cve_parse_error:
                    self.logger.warning("Ignoring CVE of : {}".format(cve_string))

                    # Let's See if Launchpad is at play here
                    if cve_string.startswith("https://launchpad.net/bugs"):
                        # It's Launchpad Let's ad the Link when we ignore
                        lp_num = cve_string.split("/")[-1]
                        usn_data["reference_links"]["LP : {}".format(lp_num)] = str(cve_string)
                    else:
                        # Add it as itself
                        usn_data["reference_links"][str(cve_string)] = str(cve_string)

                else:
                    usn_data["parsed_cves"].append(this_cve_obj)

                    if int(this_cve_obj.best_numeric_score()) > highest_priority:
                        highest_priority = int(this_cve_obj.best_numeric_score())

                    # Add CVE Link to References
                    usn_data["reference_links"]["{}_({})".format(this_cve_obj.cve_id.upper(), this_cve_obj.get_severity().capitalize())] = this_cve_obj.primary_reference

                    self.logger.info("{} : {} ({:.2}) added.".format(this_cve_obj.cve_id.upper(),
                                                                  this_cve_obj.get_severity().capitalize(),
                                                                  this_cve_obj.best_numeric_score()))

            usn_data["highest_priority"] = highest_priority

        return usn_data

    def cal_bucket_defs(self):

        '''
        Given the data in self.usn_data return the bucket definitions for filters and comparisons tuple of dicts
        '''

        comparisons = dict()
        filters = dict()

        for this_release in self.usn_data["releases"].keys():

            bucket_name = "{}-bucket".format(this_release)

            if bucket_name not in filters.keys():

                # Populate Blank Buckets/Comparisons
                filters[bucket_name] = {"filter-collection-type" : ["os", "release"],
                                        "filter-collection-subtype" : ["default", "default"],
                                        "filter-match-value" : ["Ubuntu", this_release],
                                        "filter-match" : "is"}

                comparisons[bucket_name] = {"comparison-collection-type" : list(),
                                            "comparison-collection-subtype" : list(),
                                            "comparison-match-value" : list(),
                                            "comparison-match" : "aptge"}

            for package in self.usn_data["releases"][this_release]["binaries"].keys():
                # For Each Package populate it's relevant comparison
                self.logger.debug("Release {}: Package : {}".format(this_release, package))
                comparisons[bucket_name]["comparison-collection-type"].append("packages")
                comparisons[bucket_name]["comparison-collection-subtype"].append(package)
                comparisons[bucket_name]["comparison-match-value"].append(self.usn_data["releases"][this_release]["binaries"][package]["version"])

        return (filters, comparisons)

    def handle_local_cache(self):

        '''
        1. See if the Cache File is Recent and Exists
        1. Download if Missing
        '''

        now = int(time.time())

        get_file = False

        if self.cachefile is not None:

            if os.path.isfile(self.cachefile):
                file_create_time = os.path.getmtime(self.cachefile)

                time_left = file_create_time - (now - self.cacheage)

                self.logger.info("File has {} Seconds before expiration.".format(time_left))

                if time_left <= 0:
                    self.logger.info("File {} seconds {} too old. Pulling New Version.".format(abs(time_left), self.cachefile))

                    get_file = True

                else:
                    self.logger.debug("File {} new enough. {} seconds left.".format(self.cachefile, time_left))
            else:
                self.logger.debug("File {} missing. Pulling it.".format(self.cachefile))
                get_file = True
        else:
            self.logger.debug("Not cacheing results to disk.")
            get_file = True


        if get_file is True:

            try:
                response = requests.get(self.__usn_url)
            except Exception as get_json_error:
                self.logger.error("Unable to Get usn db with error : {}".format(get_json_error))
                raise get_json_error
            else:
                if response.status_code == requests.codes.ok:
                    self.logger.info("Writing new Cache File.")

                    if self.cachefile is not None:
                        self.logger.info("Persistent Cache File Requested, utilizing")
                        with open(self.cachefile, "wb") as new_cachefile:
                            new_cachefile.write(response.content)

                    self.cachedata = response.json()

                else:
                    self.logger.error("Error getting DB. HTTP Response Code {}".format(response.status_code))
                    raise ValueError("Response {} Recieved".format(respone.status_code))
            finally:
                self.logger.debug("Upstream Data Acquired.")


if __name__ == "__main__" :

    my_usn = AuditSourceUSN(source_key=USN, cachefile=CACHEFILE, cacheage=CACHEAGE)

    validated = my_usn.validate_audit_live()

    LOGGER.info("validated : {}".format(validated))

    print(json.dumps(my_usn.return_audit()))





