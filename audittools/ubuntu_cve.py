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

    LOGGER = logging.getLogger("ubuntu_cve.py")

    LOGGER.debug("Welcome to Ubuntu CVE.")

class mowCVEUbuntu(mowCVE):

    '''
    Ubuntu CVE Class that Updates mowCVE with Data from CVE
    '''

    # Case Insensitive
    #__okay_severities = ["unknown", "none", "low", "medium", "high", "critical"]

    __ubuntu_cve_endpoint = "https://git.launchpad.net/ubuntu-cve-tracker/plain/active/"

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

        # Don't Run When Testing
        if kwargs.get("test", False) is False:
            self.pull_ubuntu_cve()

    def pull_ubuntu_cve(self):

        '''
        Reach out, Grab the CVE Data and Parse it
        '''

        ubuntu_url = urljoin(self.__ubuntu_cve_endpoint, self.cve_id)

        parsed_data = None

        try:
            response = requests.get(ubuntu_url)
        except Exception as url_error:
            self.logger.error("Unable to Query Ubuntu for CVE : {}".format(self.cve_id))
            self.logger.debug("Query Error for CVE {} : {}".format(self.cve_id, url_error))
        else:

            if response.status_code == requests.codes.ok:
                # Good Data
                data = response.text

                try:

                    # Manipulate For Config Parser
                    data = "[{}]\n".format(self.cve_id) + data

                    cve_data_parsed = ConfigParser()
                    cve_data_parsed.read_string(data)
                except Exception as parsing_error:
                    self.logger.error("Unable to Read CVE {} with Error {}".format(self.cve_id, parsing_error))
                else:
                    self.logger.debug("Pulled Data from Ubuntu about CVE {}".format(self.cve_id))
                    parsed_data = dict(cve_data_parsed._sections[self.cve_id])

                    self.enhance_cve(parsed_cve_data=parsed_data, ubuntu_url=ubuntu_url)

            elif response.status_code == 404:
                self.logger.warning("CVE {} Not found on Ubuntu Site.".format(self.cve_id))
            else:
                self.logger.error("CVE {} unable to Query for CVE Recieved {}".format(self.cve_id, response.status_code))
        finally:
            pass


    def enhance_cve(self, parsed_cve_data=None, ubuntu_url=None):

        '''
        Takes the parsed Data and Updates all the various bits
        '''

        self.title = "Ubuntu's {}".format(self.cve_id)
        self.description = parsed_cve_data["description"]

        if parsed_cve_data["priority"] in self._okay_severities:
            self.severity_override = parsed_cve_data["priority"]
            self.score_override = self._okay_severities.index(parsed_cve_data["priority"]) * 1.9

        readable_url = "https://people.canonical.com/~ubuntu-security/cve/{}/CVE-{}-{}.html".format(self.cve_year, self.cve_year, self.cve_num)
        self.references = {"{} Data".format(self.title) : ubuntu_url, self.title : readable_url}
        self.primary_reference = readable_url

        for reference_url in parsed_cve_data["references"].split():
            if len(reference_url) >= 0:
                self.references[reference_url] = reference_url

        try:
            updated_date = datetime.datetime.strptime(parsed_cve_data["publicdate"], "%Y-%m-%d %H:%M:%S UTC")
        except Exception as date_error:
            self.logger.warning("Unable to Read date of {}".format(parsed_cve_data["publicdate"]))
            self.logger.debug("Date Error {}".format(date_error))
        else:
            self.last_updated = int(updated_date.timestamp())

        ## Now Let's Do Filters and Comparisons

        # Getting Package Patches Tracked in This CVE
        filters = dict()
        comparisons = dict()

        any_patches = False

        for potential_pkg in parsed_cve_data.keys():
            if potential_pkg.startswith("patches_"):
                # Found a Patch
                this_package_name = potential_pkg.split("_")[1]

                # Now Search for All the Release that this Patch has been Seen in.
                for potential_package_patch in parsed_cve_data.keys():
                    if potential_package_patch.endswith(this_package_name):

                        this_release = potential_package_patch.split("_")[0]

                        if this_release.endswith("/esm"):
                            # I have an ESM Package Alter the this_release value
                            this_release = this_release.split("/")[0]


                        if this_release in ("upstream", "devel", "patches"):
                            # Ignore the Upstream Data
                            pass
                        else:
                            # Legit Thing
                            status_string = parsed_cve_data[potential_package_patch]


                            try:
                                fixed_version = re.search("released \((.+)\)", status_string, re.IGNORECASE).group(1)
                            except Exception as fixed_version_error:
                                self.logger.debug("Unable to Find version for {} in {}".format(this_package_name, this_release))
                            else:
                                self.logger.info("{} Found a Patch for Package Named {} in release {}".format(self.cve_id, this_package_name, this_release))

                                any_patches = True
                                # I have a Fixed Item

                                # Okay Now I have a Patched Item. I need to both ensure that
                                # I have a filter/bucket for my this_release and create/add this package
                                # to my comparison/bucket for this package
                                bucket_name = "{}-bucket".format(this_release)
                                if bucket_name not in filters.keys():
                                    # This is the First Time I'm seeing this Release
                                    filters[bucket_name] = {"filter-collection-type" : ["os", "release"],
                                                            "filter-collection-subtype" : ["default", "default"],
                                                            "filter-match-value" : ["Ubuntu", this_release],
                                                            "filter-match" : "is"}

                                    comparisons[bucket_name] = {"comparison-collection-type" : list(),
                                                               "comparison-collection-subtype" : list(),
                                                               "comparison-match-value" : list(),
                                                               "comparison-match" : "aptge"}

                                # I've Added nake filters and comparisons for my bucket so
                                comparisons[bucket_name]["comparison-collection-type"].append("packages")
                                comparisons[bucket_name]["comparison-collection-subtype"].append(this_package_name)
                                comparisons[bucket_name]["comparison-match-value"].append(fixed_version)

        if any_patches is True:
            self.filters = filters
            self.comparisons = comparisons
        else:
            self.logger.warning("No Active Patches found for this CVE")

if __name__ == "__main__" :

    my_usn = mowCVEUbuntu(cve=CVE)

    print(json.dumps(my_usn.summarize(), sort_keys=True, indent=2))
    #print(my_usn.get_severity())
    #print(my_usn.best_numeric_score())

