#!/usr/bin/env python3

'''
A new Ubuntu CVE different than shuttlefish. Utilizes Launchpad data to grab Ubuntu
CVE Data
'''

import time
import logging
import re

import cvss
import cpe
# Library doesn't exist
# import capec

class mowCVE:

    '''
    Generic CVE Class To Expand Upon Includes Bits for Auditing

    Creation
    '''

    # Case Insensitive
    _okay_severities = ["unknown", "none", "low", "medium", "high", "critical"]
    _cve_regex = "[Cc][Vv][Ee]-(\d+)-(\d+)"

    logger = logging.getLogger("mowCVE")

    def __init__(self, cve=None, **kwargs):

        '''
        Initialze a Holder for CVE Things
        '''


        if cve is None:
            raise ValueError("CVE ID Required")

        try:
            cve_parts = re.search(self._cve_regex, cve, re.I)
        except Exception as cve_parse_error:
            self.logger.error("Unable to Parse CVE : {}".format(cve))
            raise ValueError("Badly Formatted CVE")
        else:
            if cve_parts is not None:
                self.cve_id = cve.upper()
                self.cve_year = int(cve_parts.group(1))
                self.cve_num = int(cve_parts.group(2))
            else:
                raise ValueError("Valid CVE ID Required, Recieved {}".format(cve))

        self.description = kwargs.get("description", None)
        self.title = kwargs.get("title", None)

        if isinstance(kwargs.get("cvss2", None), str):
            self.cvss2 = cvss.CVSS2(kwargs["cvss2"])
        elif isinstance(kwargs.get("cvss2", None), cvss.CVSS2):
            self.cvss2 = kwargs["cvss2"]
        else:
            self.cvss2 = None

        if isinstance(kwargs.get("cvss3", None), str):
            self.cvss3 = cvss.CVSS3(kwargs["cvss3"])
        elif isinstance(kwargs.get("cvss3", None), cvss.CVSS3):
            self.cvss3 = kwargs["cvss3"]
        else:
            self.cvss3 = None

        self.severity_override = kwargs.get("severity_override", None)
        self.score_override = kwargs.get("score_override", None)
        self.cpe_list = [cpe.CPE(indv_cpe) for indv_cpe in kwargs.get("cpe_list", list())]
        self.capec_list = kwargs.get("capec_list", list())
        self.cwe_list = kwargs.get("cwe_list", list())
        self.references = kwargs.get("references", dict())
        self.primary_reference = kwargs.get("primary_reference", None)
        self.last_updated = kwargs.get("last_updated", None)
        self.published = kwargs.get("published", None)

        # Updated Now!
        self.self_updated = int(time.time())

        # Audit Items
        self.filters = kwargs.get("bucket_def", {})
        self.comparisons = kwargs.get("comparisons", {})

    def summarize(self):

        '''
        Give a Dict Summarization
        '''

        the_thing = {"cve_id" : self.cve_id,
                     "title" : self.title,
                     "description" : self.description,
                     "severity_override" : self.severity_override,
                     "score_override" : self.score_override,
                     "cpe_list" : [plat.as_uri_2_3() for plat in self.cpe_list],
                     "capec_list" : self.capec_list,
                     "cwe_list" : self.cwe_list,
                     "references" : self.references,
                     "primary_reference" : self.primary_reference,
                     "last_updated" : self.last_updated,
                     "published" : self.published,
                     "self_updated" : self.self_updated,
                     "filters" : self.filters,
                     "comparisons" : self.comparisons
                    }

        if self.cvss2 is not None:
            the_thing["cvss2"] = self.cvss2.clean_vector()
        if self.cvss3 is not None:
            the_thing["cvss3"] = self.cvss3.clean_vector()

        return the_thing

    def get_severity(self):

        '''
        Logic to Return the "Right" Severity"
        '''

        best_severity = "unknown"
        # Best Severity

        if self.severity_override is not None and self.severity_override.lower() in self._okay_severities:
            best_severity = self.severity_override
        elif self.cvss3 is not None:
            best_severity = self.cvss3.severities()[-1].lower()
        elif self.cvss2 is not None:
            cvss2_severity_num = self.cvss2.scores()[-1]

            if cvss2_severity_num <= 3.9:
                best_severity = "low"
            elif cvss2_severity_num <= 6.9:
                best_severity = "medium"
            elif cvss2_severity_num <= 10:
                best_severity = "high"

        else:
            self.logger.warning("No Severity Found returning Unknown")

        return best_severity

    def best_numeric_score(self):

        '''
        Best Out of 10 Numeric Score
        '''

        best_score = 0.1
        # Best Severity

        if isinstance(self.score_override, (float, int)) and self.score_override >= 0.0 and self.score_override <= 10.0:
            best_score = self.score_override
        elif self.cvss3 is not None:
            best_score = self.cvss3.scores()[-1]
        elif self.cvss2 is not None:
            best_score = self.cvss2.scores()[-1]
        else:
            self.logger.warning("No Severity Found returning 0.1")

        return best_score
