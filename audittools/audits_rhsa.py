#!/usr/bin/env python3

'''
audits_rhsa.py

Given a Single RHSA let's create an manowar audit that represents that.
'''

import argparse
import json
import logging
import os
import os.path
import time
import re
import packaging.version


from urllib.parse import urljoin

import requests

if __name__ == "__main__":
    from audit_source import AuditSource
    from redhat_cve import mowCVERedHat
else:
    from audittools.audit_source import AuditSource
    from audittools.redhat_cve import mowCVERedHat



if __name__ == "__main__" :
    parser = argparse.ArgumentParser()
    #parser.add_argument("-v", "--verbose", action='store_true', help="Turn on Verbosity")
    parser.add_argument("-v", "--verbose", action='append_const', help="Turn on Verbosity", const=1, default=[])
    parser.add_argument("-r", "--rhsa", required=True)

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

    RHSA = args.rhsa

    LOGGER = logging.getLogger("audits_rhsa.py")

    LOGGER.debug("Welcome to Audits RHSA.")

class AuditSourceRHSA(AuditSource):

    '''
    Implements a Public AuditSource object for Ubuntu Security Notices
    '''

    __rhsa_regex = r"[Rr][Hh][Ss][Aa]-\d{4}\:\d{1,6}"
    __redhat_security_endpoint = "https://access.redhat.com/hydra/rest/securitydata/cvrf/"

    __epoch_regex = "^(\d)\:"
    __el_regex = "^(\S+)\.el(\d{0,2})"


    def __init__(self, **kwargs):

        # Run My Parent Init Function
        AuditSource.__init__(self, **kwargs)

        # Confirm I have a USN
        if re.match(self.__rhsa_regex, self.source_key) is None:
            raise ValueError("Source Key Doesn't look like a RHSA {}".format(str(self.source_key)))

        self.rhsa_filters = dict()
        self.rhsa_comparisons = dict()

        self.rhsa_data = self.get_rhsa_data()

        self.populate_audit()

    def populate_audit(self):

        '''
        Assuming I have my USN Data as a Dictionary, Let's populate the self.audit_data & self.audit_name items from my
        parent function.
        '''

        self.audit_name = self.rhsa_data["cvrfdoc"]["document_title"]


        self.audit_data = {**self.audit_data,
                           "vuln-name" : self.audit_name,
                           "vuln-primary-link" : self.rhsa_data["cvrfdoc"]["document_references"]["reference"][0]["url"],
                           "vuln-additional-links" : self.rhsa_data["reference_links"],
                           "vuln-short-description" : self.rhsa_data["cvrfdoc"]["document_notes"]["note"][0],
                           "vuln-priority" : self.rhsa_data["highest_priority"],
                           "filters": self.rhsa_filters,
                           "comparisons": self.rhsa_comparisons}

        self.audit_data["vuln-long-description"] = "\n\n".join(self.rhsa_data["cvrfdoc"]["document_notes"]["note"])

        return

    def get_rhsa_data(self):

        '''
        Turn the RHSA to an Audit Dictionary of type {"usn-number" : <data...>}
        '''

        if self.source_key is None:
            raise ValueError("Unknown USN")

        endpoint = "{}{}.json".format(self.__redhat_security_endpoint, self.source_key)
        rhsa_data = dict()


        try:

            self.logger.debug("Requesting {} URL of {}".format(self.source_key, endpoint))
            response = requests.get(endpoint)

        except Exception as get_hrsa_url_error:
            self.logger.error("Error when Requesting data for RHSA {}".format(self.source_key))
            self.logger.info("Error for RHSA Request : {}".format(get_hrsa_url_error))
        else:
            if response.status_code == requests.codes.ok:
                # Good Data
                rhsa_data = response.json()

            elif response.status_code == 404:
                self.logger.warning("RHSA {} Not found on Red Hat Site.".format(self.source_key))
            else:
                self.logger.error("RHSA {} unable to Query for RHSA Recieved {}".format(self.source_key, response.status_code))
        finally:

            self.logger.info(rhsa_data)

            rhsa_data["reference_links"] = dict()
            rhsa_data["cves"] = list()

            # Document Links Population
            for this_reference in rhsa_data["cvrfdoc"]["document_references"]["reference"]:
                rhsa_data["reference_links"][this_reference["description"]] = this_reference["url"]

            # Documentation Links in Vulnerability
            # Also Do the Buckets/Packages

            comparisons = dict()
            filters = dict()

            highest_priority = 1

            for this_vuln in rhsa_data["cvrfdoc"]["vulnerability"]:

                for this_reference in this_vuln["references"].get("reference", list()):
                    rhsa_data["reference_links"][this_reference["description"]] = this_reference["url"]

                if "cve" in this_vuln.keys():
                    this_cve = mowCVERedHat(cve=this_vuln["cve"])

                    self.logger.debug(this_cve.rh_cust_package_fixed)

                    if self.source_key in this_cve.rh_cust_package_fixed.keys():
                        for package_string in this_cve.rh_cust_package_fixed[self.source_key]:

                            try:
                                cve_split = self.break_package_release(package_string, extended=False)
                            except Exception as cve_package_parse_error:
                                self.logger.error("From CVE {} Found Package {} that has a parse error.".format(this_cve.cve_id,
                                                                                                                package_string))
                                self.logger.debug("From CVE {} Found Package {} that has a parse error {}.".format(this_cve.cve_id,
                                                                                                                   package_string))
                            else:
                                self.insert_into_matrix(**cve_split)


                for this_product_vuln in this_vuln["product_statuses"]["status"]["product_id"]:

                    if this_vuln["product_statuses"]["status"]["type"] == "Fixed":
                        # This is a Fixed Vuln

                        try:
                            i_split = self.break_package_release(this_product_vuln, extended=True)
                        except Exception as parse_error:
                            self.logger.error("Not parsing {} as I ran into an issue.".format(this_product_vuln))
                            self.logger.info("Error {} when parsing {}".format(parse_error, this_product_vuln))
                        else:
                            # I split it well let's put it in the buckets/keys

                            self.insert_into_matrix(**i_split)

                    else:
                        self.logger.warning("Ignoring Product {} as it's not listed as fixed.".format(this_product_vuln))


                    this_prioirty = this_vuln.get("threats", dict()).get("ordinal", 0)
                    if this_prioirty > highest_priority:
                        highest_priority = this_priority

            rhsa_data["filters"] = filters
            rhsa_data["comparisons"] = comparisons
            rhsa_data["highest_priority"] = highest_priority

        return rhsa_data

    def insert_into_matrix(self, bucket_name=None, release_number=None, package=None, version=None, **kwargs):

        '''
        Insert a Package into the comparisons and filters
        '''

        self.logger.debug("{}, {}, {}, {}".format(bucket_name, release_number, package, version))

        if bucket_name not in self.rhsa_filters.keys():
            # Add my Items
            self.rhsa_filters[bucket_name] = {"filter-collection-type" : ["os_family", "os_release"],
                                              "filter-collection-subtype" : ["default", "default"],
                                              "filter-match-value" : ["RedHat", release_number],
                                              "filter-match" : "is"}

            self.rhsa_comparisons[bucket_name] = {"comparison-collection-type" : list(),
                                                  "comparison-collection-subtype" : list(),
                                                  "comparison-match-value" : list(),
                                                  "comparison-match" : "aptge"}

        if package in self.rhsa_comparisons[bucket_name]["comparison-collection-subtype"]:
            # Duplicate Package
            package_index = self.rhsa_comparisons[bucket_name]["comparison-collection-subtype"].index(package)


            current_version = packaging.version.parse(self.rhsa_comparisons[bucket_name]["comparison-match-value"][package_index])
            new_version = packaging.version.parse(version)

            if current_version > new_version:
                self.logger.debug("Replacing definition for {} in bucket {}".format(package, bucket_name))
                self.rhsa_comparisons[bucket_name]["comparison-match-value"][package_index] = version
            else:
                self.logger.info("Duplicate definition for {} in bucket {} ignored.".format(package, bucket_name))
        else:
            # New Add
            self.logger.debug("Adding definition in bucket {} for package {} & version {}".format(bucket_name, package, version))

            self.rhsa_comparisons[bucket_name]["comparison-collection-type"].append("packages")
            self.rhsa_comparisons[bucket_name]["comparison-collection-subtype"].append(package)
            self.rhsa_comparisons[bucket_name]["comparison-match-value"].append(version)

        return

    def break_package_release(self, package_text, extended=True):

        '''
        Takes a package text like : 7Server-7.6.EUS:kpatch-patch-3_10_0-957_38_1-0:1-3.el7 or kernel-2.6.32-754.24.2.el6
        And breaks it down into it's component pices. Giving you a Bucket, Package & Version that should be "consistent"
        '''

        self.logger.debug("Package Text {}".format(package_text))

        if extended is True:
            application_stream = package_text.split(":")[0]

            self.logger.debug("Ignoring Application Stream data of {}".format(application_stream))

            fixed_product = ":".join(package_text.split(":")[1:])
        else:

            application_stream = "ns"
            fixed_product = package_text

        product_regex = re.match(self.__el_regex, str(fixed_product))

        if product_regex is not None:
            release_number = int(product_regex.group(2))
            package_n_version = product_regex.group(1)

        self.logger.debug("Found Package for Release {} : {}".format(release_number, package_n_version))

        # Split Package Name from Version
        pnv_array = package_n_version.split("-")

        for chunk_index in range(1, len(pnv_array)-1):
            if pnv_array[chunk_index][0].isdigit():
                # This is the chunk that starts the version
                package = "-".join(pnv_array[:chunk_index])
                full_version = "-".join(pnv_array[chunk_index:])
                best_version = full_version


                if re.match(self.__epoch_regex, full_version) is not None:
                    best_version = full_version.split(":")[1]
                    epoch = full_version.split(":")[0]
                else:
                    epoch = None

                if len(best_version.split("-")) == 2:
                    version_release = best_version.split("-")[1]
                    best_version = best_version.split("-")[0]
                else:
                    version_release = None

                break



        bucket_name = "{}-bucket".format(release_number)


        return_data = {"application_stream" : application_stream,
                       "bucket_name" : bucket_name,
                       "package" : package,
                       "version" : best_version,
                       "full_version" : full_version,
                       "release_number" : release_number,
                       "version_release" : version_release,
                       "epoch" : epoch}

        return return_data



if __name__ == "__main__" :

    my_rhsa = AuditSourceRHSA(source_key=RHSA)

    #validated = my_usn.validate_audit_live()

    #LOGGER.info("validated : {}".format(validated))

    print(json.dumps(my_rhsa.return_audit(), indent=2, sort_keys=True))





