#!/usr/bin/env python3

'''
A new Ubuntu CVE different than shuttlefish. Utilizes Launchpad data to grab Ubuntu
CVE Data
'''

import time
import logging
import argparse
import re
import datetime
import json

from urllib.parse import urljoin
from configparser import ConfigParser

import cvss
import cpe
import requests

# Library doesn't exist
# import capec
if __name__ in ["__main__", "ubuntu_cve", "redhat_cve"]:
    from cve_class import mowCVE
else:
    from audittools.cve_class import mowCVE

if __name__ == "__main__" :
    parser = argparse.ArgumentParser()
    #parser.add_argument("-v", "--verbose", action='store_true', help="Turn on Verbosity")
    parser.add_argument("-v", "--verbose", action='append_const', help="Turn on Verbosity", const=1, default=[])
    parser.add_argument("-c", "--cve", required=True)

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

    CVE = args.cve

    LOGGER = logging.getLogger("redhat_cve.py")

    LOGGER.debug("Welcome to RedHat CVE.")

class mowCVERedHat(mowCVE):

    '''
    Red Hat CVE Class that Updates mowCVE with Data from CVE
    '''

    # Case Insensitive
    #__okay_severities = ["unknown", "none", "low", "medium", "high", "critical"]

    __redhat_security_endpoint = "https://access.redhat.com/hydra/rest/securitydata/cve/"
    __redhat_cve_hr = "https://access.redhat.com/security/cve"

    def __init__(self, cve=None, **kwargs):

        '''
        Initialze a Holder for CVE Things
        '''

        if cve is None:
            raise ValueError("CVE ID Required")

        mowCVE.__init__(self, cve=cve, **kwargs)

        '''
        self.description = kwargs.get("description", None)
        self.title = kwargs.get("title", None)
        self.cvss2 = cvss.CVSS2(kwargs.get("cvss2", None))
        self.cvss3 = cvss.CVSS3(kwargs.get("cvss3", None))
        self.severity_override = kwargs.get("severity_override", None)
        self.score_override = kwargs.get("score_override", None)
        self.cpe_list = [cpe.CPE(indv_cpe) for indv_cpe in kwargs.get("cpe_list", list())]
        self.capec_list = kwargs.get("capec_list", list())
        self.references = kwargs.get("references", dict())
        self.primary_reference = kwargs.get("primary_reference", None)
        self.last_updated = kwargs.get("last_updated", None)
        self.published = kwargs.get("published", None)

        # Updated Now!
        self.self_updated = int(time.time())

        # Audit Items
        self.filters = kwargs.get("bucket_def", {})
        self.comparisons = kwargs.get("comparisons", {})
        '''

        # Default Custom Thing
        self.rh_cust_package_fixed = dict()


        # Don't Run When Testing
        if kwargs.get("test", False) is False:
            self.pull_rh_cve()

    def pull_rh_cve(self):

        '''
        Reach out, Grab the CVE Data and Parse it
        '''

        rh_endpoint = urljoin(self.__redhat_security_endpoint, "{}.json".format(self.cve_id))

        self.logger.debug("RH API Call : {}".format(rh_endpoint))

        parsed_data = None

        try:
            response = requests.get(rh_endpoint)
        except Exception as url_error:
            self.logger.error("Unable to Query Red Hat Data for CVE : {}".format(self.cve_id))
            self.logger.debug("Query Error for CVE {} : {}".format(self.cve_id, url_error))
        else:

            if response.status_code == requests.codes.ok:
                # Good Data
                parsed_data = response.json()

                self.enhance_cve(parsed_cve_data=parsed_data, rh_url=rh_endpoint)

            elif response.status_code == 404:
                self.logger.warning("CVE {} Not found on Red Hat Site.".format(self.cve_id))
            else:
                self.logger.error("CVE {} unable to Query for CVE Recieved {}".format(self.cve_id, response.status_code))
        finally:
            pass



    def enhance_cve(self, parsed_cve_data=None, rh_url=None):

        '''
        Takes the parsed Data and Updates all the various bits
        '''

        self.title = parsed_cve_data["name"]

        self.description = "\n\n".join(parsed_cve_data["details"])

        if "cvss3" in parsed_cve_data.keys():
            self.cvss3 = cvss.CVSS3(parsed_cve_data["cvss3"]["cvss3_scoring_vector"])

        if "cwe" in parsed_cve_data.keys():
            self.cwe_list = parsed_cve_data["cwe"].split("->")


        readable_url = urljoin(self.__redhat_cve_hr, self.cve_id)

        self.references = {"Red Hat {}".format(self.cve_id) : readable_url,
                           "{} API".format(self.cve_id) : rh_url}


        self.primary_reference = readable_url

        if "bugzilla" in parsed_cve_data.keys():
            self.references["RH Bugzilla {}".format(parsed_cve_data["bugzilla"]["id"])] = parsed_cve_data["bugzilla"]["url"]

        try:
            updated_date = datetime.datetime.strptime(parsed_cve_data["public_date"], "%Y-%m-%dT%H:%M:%SZ")
        except Exception as date_error:
            self.logger.warning("Unable to Read date of {}".format(parsed_cve_data["publicdate"]))
            self.logger.debug("Date Error {}".format(date_error))
        else:
            self.published = int(updated_date.timestamp())

        for package in [*parsed_cve_data.get("package_state", list()), *parsed_cve_data.get("affected_release", list())]:
            try:
                self.cpe_list.append(cpe.CPE(package["cpe"]))
            except Exception as cpe_error:
                self.logger.error("CPE Error {} with CPE {}".format(cpe_error, package["cpe"]))
            else:
                if "package" in package.keys() and "advisory" in package.keys():
                    self.logger.debug("Found package fix for package {} and advisory {}".format(package["package"],
                                                                                                package["advisory"]))

                    if package["advisory"] not in self.rh_cust_package_fixed.keys():
                        self.rh_cust_package_fixed[package["advisory"]] = list()

                    self.rh_cust_package_fixed[package["advisory"]].append(package["package"])



if __name__ == "__main__" :

    my_usn = mowCVERedHat(cve=CVE)

    print(json.dumps(my_usn.summarize(), sort_keys=True, indent=2, default=str))

