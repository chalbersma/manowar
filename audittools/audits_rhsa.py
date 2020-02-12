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
import datetime
import packaging.version


from urllib.parse import urljoin

import requests

if __name__ == "__main__":
    from audit_source import AuditSource
    from redhat_cve import mowCVERedHat
else:
    from audittools.audit_source import AuditSource
    from audittools.redhat_cve import mowCVERedHat


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # parser.add_argument("-v", "--verbose", action='store_true', help="Turn on Verbosity")
    parser.add_argument("-v", "--verbose", action='append_const',
                        help="Turn on Verbosity", const=1, default=[])
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
    __redhat_oval_endpoint = "https://access.redhat.com/hydra/rest/securitydata/oval/"
    __ts_format = "%Y-%m-%dT%H:%M:%SZ"

    __epoch_regex = "^(\d)\:"
    __el_regex = "^(\S+)[\.\+]el(\d{0,2})"

    def __init__(self, **kwargs):

        # Run My Parent Init Function
        AuditSource.__init__(self, **kwargs)

        # Confirm I have a USN
        if re.match(self.__rhsa_regex, self.source_key) is None:
            raise ValueError(
                "Source Key Doesn't look like a RHSA {}".format(str(self.source_key)))

        self.rhsa_filters = dict()
        self.rhsa_comparisons = dict()

        self.rhsa_data = self.get_rhsa_data()
        self.oval_data = self.get_oval_data()

        self.populate_audit()

    def populate_audit(self):
        '''
        Assuming I have my USN Data as a Dictionary, Let's populate the self.audit_data & self.audit_name items from my
        parent function.
        '''

        self.audit_name = self.source_key

        self.audit_data = {**self.audit_data,
                           "vuln-name": self.audit_name,
                           "vuln-primary-link": self.rhsa_data["cvrfdoc"]["document_references"]["reference"][0]["url"],
                           "vuln-additional-links": self.rhsa_data["reference_links"],
                           "vuln-short-description": self.rhsa_data["cvrfdoc"]["document_notes"]["note"][0],
                           "vuln-priority": self.rhsa_data["highest_priority"],
                           "filters": self.rhsa_filters,
                           "comparisons": self.rhsa_comparisons}

        audit_date = datetime.datetime.strptime(self.oval_data["data"]["oval_definitions"]["generator"]["oval:timestamp"], self.__ts_format)
                                                                                                
        self.audit_data["auditts"] = int(audit_date.timestamp())

        self.audit_data["vuln-long-description"]= "\n\n".join(self.rhsa_data["cvrfdoc"]["document_notes"]["note"])

        return

    def get_rhsa_data(self):

        '''
        Turn the RHSA to an Audit Dictionary of type {"usn-number" : <data...>}
        '''

        if self.source_key is None:
            raise ValueError("Unknown USN")

        endpoint= "{}{}.json".format(self.__redhat_security_endpoint, self.source_key)
        rhsa_data= dict()


        try:

            self.logger.debug("Requesting {} URL of {}".format(
                self.source_key, endpoint))
            response= requests.get(endpoint)

        except Exception as get_hrsa_url_error:
            self.logger.error(
                "Error when Requesting data for RHSA {}".format(self.source_key))
            self.logger.info(
                "Error for RHSA Request : {}".format(get_hrsa_url_error))
        else:
            if response.status_code == requests.codes.ok:
                # Good Data
                rhsa_data= response.json()

            elif response.status_code == 404:
                self.logger.warning(
                    "RHSA {} Not found on Red Hat Site.".format(self.source_key))
            else:
                self.logger.error("RHSA {} unable to Query for RHSA Recieved {}".format(
                    self.source_key, response.status_code))
        finally:

            self.logger.info(rhsa_data)

            rhsa_data["reference_links"]= dict()
            rhsa_data["cves"]= list()

            # Document Links Population
            for this_reference in rhsa_data["cvrfdoc"]["document_references"]["reference"]:
                rhsa_data["reference_links"][this_reference["description"]]= this_reference["url"]

            # Documentation Links in Vulnerability
            # Also Do the Buckets/Packages

            comparisons= dict()
            filters= dict()

            highest_priority= 1

            for this_vuln in rhsa_data["cvrfdoc"]["vulnerability"]:

                for this_reference in this_vuln["references"].get("reference", list()):
                    rhsa_data["reference_links"][this_reference["description"]]= this_reference["url"]

                if "cve" in this_vuln.keys():
                    this_cve= mowCVERedHat(cve=this_vuln["cve"])
                    rhsa_data["RHCVE : {}".format(this_cve.cve_id)]= this_cve.primary_reference

                for this_product_vuln in this_vuln["product_statuses"]["status"]["product_id"]:

                    this_prioirty= this_vuln.get("threats", dict()).get("ordinal", 0)
                    if this_prioirty > highest_priority:
                        highest_priority= this_priority

            rhsa_data["highest_priority"]= highest_priority

        return rhsa_data

    def get_oval_data(self):

        '''
        Gets the OVAL data for this Finding
        '''

        endpoint= "{}{}.json".format(self.__redhat_oval_endpoint, self.source_key)

        oval_data = {"has_oval": False}

        try:
            self.logger.debug("Requesting {} URL of {}".format(
                self.source_key, endpoint))
            response= requests.get(endpoint)
        except Exception as get_oval_url_error:
            self.logger.error(
                "Error when Requesting OVAL data for RHSA {}".format(self.source_key))
            self.logger.info(
                "Error for RHSA OVAL Request : {}".format(get_hrsa_url_error))
        else:
            if response.status_code == requests.codes.ok:
                # Good Data
                oval_data["data"]= response.json()
                if oval_data["data"].get("message", None) == "Not Found":
                    oval_data["has_oval"]= False
                    self.logger.warning(
                        "RHSA {} has no OVAL data for this valid RHSA.".format(self.source_key))
                else:
                    oval_data["has_oval"]= True

            elif response.status_code == 404:
                self.logger.warning(
                    "RHSA {} has no OVAL data.".format(self.source_key))
            else:
                self.logger.error("RHSA {} unable to Query for RHSA Recieved {}".format(
                    self.source_key, response.status_code))

        finally:

            if oval_data["has_oval"] is True:

                self.logger.debug(
                    "RHSA {} has Oval Data.".format(self.source_key))

                # " packages -> releases -> comparisons "
                versions_matrix= dict()

                for oval_comparison in oval_data["data"]["oval_definitions"]["states"].get("rpminfo_state", list()):
                    self.logger.debug("Found oval comparison thing for Comparsion named : {}".format(
                        oval_comparison["id"]))
                    versions_matrix[oval_comparison["id"]]= oval_comparison

                    if "evr" not in oval_comparison:
                        # It's really just useless to me.
                        versions_matrix[oval_comparison["id"]]["isversion"]= False
                    else:
                        versions_matrix[oval_comparison["id"]]["isversion"]= True

                package_matrix= dict()

                for package_obj in oval_data["data"]["oval_definitions"]["objects"].get("rpminfo_object", list()):
                    self.logger.debug(
                        "Found oval for RPM Package named : {}".format(package_obj["name"]))
                    package_matrix[package_obj["id"]]= package_obj

                # Testing Comprehension
                for oval_test in oval_data["data"]["oval_definitions"]["tests"].get("rpminfo_test", list()):
                    self.logger.debug(
                        "Found oval for Test Case : {}".format(oval_test["id"]))

                    test_id= oval_test["id"]
                    tested_thing_id= oval_test["object"]["object_ref"]
                    case_covered_id= oval_test["state"]["state_ref"]

                    if versions_matrix[case_covered_id]["isversion"] is True:
                        # We Use it
                        self.logger.debug(
                            "Adding Comparison for OVAL ID {}".format(test_id))
                        i_split= self.break_package_release(extended=False,
                                                            package_name=package_matrix[tested_thing_id]["name"],
                                                            package_version=versions_matrix[case_covered_id]["evr"])

                        self.logger.debug("ISplit Found : {}".format(i_split))

                        # I have my Split let's add it
                        if i_split["full_version"] is not None:
                            self.insert_into_matrix(**i_split)
                        else:
                            self.logger.warning("Ignoring Split of {} as it has a missing Full Version.".format(i_split["package"]))
                            self.logger.debug("Bad ISplit : {}".format(i_split))

                    else:
                        self.logger.debug(
                            "Oval Test {} Isn't useful to us. Ignoring.".format(test_id))

            else:
                self.logger.debug(
                    "RHSA {} has no Oval Data but is a valid RHSA".format(self.source_key))

        return oval_data

    def insert_into_matrix(self, bucket_name=None, release_number=None, package=None, version=None, **kwargs):

        '''
        Insert a Package into the comparisons and filters
        '''

        self.logger.debug("{}, {}, {}, {}".format(
            bucket_name, release_number, package, version))

        if bucket_name not in self.rhsa_filters.keys():
            # Add my Items
            self.rhsa_filters[bucket_name] = {"filter-collection-type": ["os_family", "os_release"],
                                              "filter-collection-subtype": ["default", "default"],
                                              "filter-match-value": ["RedHat", release_number],
                                              "filter-match": "is"}

            self.rhsa_comparisons[bucket_name] = {"comparison-collection-type": list(),
                                                  "comparison-collection-subtype": list(),
                                                  "comparison-match-value": list(),
                                                  "comparison-match": "aptge"}

        if package in self.rhsa_comparisons[bucket_name]["comparison-collection-subtype"]:
            # Duplicate Package
            package_index= self.rhsa_comparisons[bucket_name]["comparison-collection-subtype"].index(package)


            current_version= packaging.version.parse(self.rhsa_comparisons[bucket_name]["comparison-match-value"][package_index])
            new_version= packaging.version.parse(version)

            if current_version > new_version:
                self.logger.debug(
                    "Replacing definition for {} in bucket {}".format(package, bucket_name))
                self.rhsa_comparisons[bucket_name]["comparison-match-value"][package_index]= version
            else:
                self.logger.info("Duplicate definition for {} in bucket {} ignored.".format(
                    package, bucket_name))
        else:
            # New Add
            self.logger.debug("Adding definition in bucket {} for package {} & version {}".format(
                bucket_name, package, version))

            self.rhsa_comparisons[bucket_name]["comparison-collection-type"].append(
                "packages")
            self.rhsa_comparisons[bucket_name]["comparison-collection-subtype"].append(
                package)
            self.rhsa_comparisons[bucket_name]["comparison-match-value"].append(
                version)

        return

    def break_package_release(self, package_text=None, extended=True, **kwargs):

        '''
        Takes a package text like : 7Server-7.6.EUS:kpatch-patch-3_10_0-957_38_1-0:1-3.el7 or kernel-2.6.32-754.24.2.el6
        And breaks it down into it's component pices. Giving you a Bucket, Package & Version that should be "consistent"
        '''

        self.logger.debug("Package Text {}".format(package_text))

        if extended is True:
            application_stream= package_text.split(":")[0]

            self.logger.debug(
                "Ignoring Application Stream data of {}".format(application_stream))

            fixed_product= ":".join(package_text.split(":")[1:])
        else:
            application_stream= "ns"
            # This will be none if I've given explicit package name and package version information
            fixed_product= package_text

        if kwargs.get("package_name", None) is None and kwargs.get("package_version", None) is None:
            # I have a package_text with package-version<bits>
            product_regex= re.match(self.__el_regex, str(fixed_product))

            if product_regex is not None:
                release_number= int(product_regex.group(2))
                package_n_version= product_regex.group(1)

            self.logger.debug("Found Package for Release {} : {}".format(release_number, package_n_version))

            # Split Package Name from Version
            pnv_array= package_n_version.split("-")

            for chunk_index in range(1, len(pnv_array)-1):
                if pnv_array[chunk_index][0].isdigit():
                    # This is the chunk that starts the version
                    package= "-".join(pnv_array[:chunk_index])
                    full_version= "-".join(pnv_array[chunk_index:])
        else:
            # I was given package and version split
            package= kwargs["package_name"]

            product_regex= re.match(self.__el_regex, str(kwargs["package_version"]))
            
            self.logger.debug("Product {} Product Version {}".format(kwargs["package_name"], kwargs["package_version"]))

            if product_regex is not None:
                release_number = int(product_regex.group(2))
                # Since I was given it split, I don't have to worry about understanding the package
                # vs. Version split. I can go straight to full_version
                full_version = product_regex.group(1)
            else:
                full_version = None
                release_number = 0


        # Okay Now let's handle Version stuff.
        best_version = full_version

        # Let's see if I have an epoch, if so let's handle that
        if full_version is not None and re.match(self.__epoch_regex, full_version) is not None:
            best_version = full_version.split(":")[1]
            epoch= full_version.split(":")[0]
        else:
            epoch= None

        # Strip out Release Information if it exists
        if best_version is not None and len(best_version.split("-")) == 2:
            version_release= best_version.split("-")[1]
            best_version= best_version.split("-")[0]
        else:
            version_release= None

        bucket_name= "{}-bucket".format(release_number)

        return_data = {"application_stream": application_stream,
                       "bucket_name": bucket_name,
                       "package": package,
                       "version": best_version,
                       "full_version": full_version,
                       "release_number": release_number,
                       "version_release": version_release,
                       "epoch": epoch}

        return return_data



if __name__ == "__main__":

    my_rhsa= AuditSourceRHSA(source_key=RHSA)

    if my_rhsa.oval_data["has_oval"] is True:

        validated= my_rhsa.validate_audit_live()

        LOGGER.info("validated : {}".format(validated))

        print(json.dumps(my_rhsa.return_audit(), indent=2, sort_keys=True))
    else:
        print(json.dumps({"no_audit": True}, indent=2, sort_keys=True))
