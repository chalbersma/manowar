#!/usr/bin/env python3

'''
Create a General Class that can be Generalized to Collect
Audits from Public Sources.
'''

import logging
import json
import configparser
import os
import os.path

import requests
import yaml

if __name__ == "__main__" or __name__ == "audit_source":
    from verifyAudits import verifySingleAudit
else:
    from audittools.verifyAudits import verifySingleAudit

class AuditSource:

    '''
    Class for Manowar Audit Creation

    Provides common fundamentals that can be utilized from different sources.
    '''

    def __init__(self, **kwargs):

        '''
        Initializes a Bare Function
        '''

        self.logger = logging.getLogger("AuditSource")

        self.source_key = kwargs.get("source_key", None)
        self.audit_name = kwargs.get("audit_name", None)

        self.audit_filename = kwargs.get("audit_filename", None)
        self.audit_path = kwargs.get("audit_path", None)

        self.audit_data = {"vuln-name" : kwargs.get("vuln-name", None),
                           "vuln-primary-link" : kwargs.get("vuln-primary-link", None),
                           "vuln-priority" : kwargs.get("vuln-priority", None),
                           "vuln-additional-links" : kwargs.get("vuln-additional-links", dict()),
                           "vuln-long-description" : None,
                           "comparisons" : kwargs.get("comparisons", dict()),
                           "filters" : kwargs.get("filters", dict()),
                           "jellyfishversion" : "2.6", }
        
        if isinstance(kwargs.get("auditts"), int):
            self.audit_data["auditts"] = kwargs["auditts"]

    def return_audit(self):

        '''
        Returns a Dictionary Form
        '''

        audit_dict = {self.audit_name : self.audit_data}

        return audit_dict

    def validate_audit_written(self):

        if self.audit_filename is None:
            raise ValueError("Audit Not Written to File")

        validated = verifySingleAudit(self.audit_filename)

        return validated

    def validate_audit_live(self):

        if self.audit_name is None:
            raise ValueError("Audit(s) Not Stored to self.audit_data")

        validated = verifySingleAudit(self.return_audit())

        return validated

    def assert_writeability(self):

        '''
        Raises an Exception if I can't Write a File
        '''

        if self.audit_filename is None:
            raise ValueError("Missing audit_filename")

        if self.audit_path is None:
            raise ValueError("Missing Audit Path.")
        else:
            if os.path.isdir(self.audit_path) is False:
                raise FileNotFoundError("Directory {} Doesn't Exist.".format(self.audit_path))

        if self.audit_name is None:
            raise ValueError("Missing Audit Name.")


    def audit_file_exists(self):

        '''
        Checks to See if a File Eixists
        '''

        exists = False

        self.assert_writeability()

        audit_file = os.path.join(self.audit_path, self.audit_filename)

        if os.path.isfile(audit_file) is True:
            exists = True

        return exists

    def write_audit(self, file_format="json"):

        written = [False, "Not Written"]

        self.assert_writeability()

        if file_format not in ("json", "yaml"):
            raise ValueError("File Format Incorrect.")

        if self.validate_audit_live() is False:
            self.logger.error("File not Written, Validation Pre-Flight Check Failed.")
            written = [False, "Validation Failure"]
        elif self.audit_file_exists() is True:
            self.logger.error("File not Written, File aready Exists.")
            written = [False, "File Pre-Exists"]
        else:
            # Okay We're Good Let's Write Stuff
            audit_file = os.path.join(self.audit_path, self.audit_filename)

            try:
                with open(audit_file, "w", encoding="utf8") as audit_file_obj:
                    if file_format is "json":
                        json.dump(self.return_audit(), audit_file_obj, sort_keys=True, indent=2)
                    elif file_format is "yaml":
                        yaml.dump(self.return_audit(), audit_file_obj, default_flow_style=False)
                    elif file_format is "ini":
                        parser = configparser.ConfigParser()

                        audit_data = self.return_audit()

                        for section in audit_data.keys():
                            parser[section] = audit_data[section]

                        parser.write(audit_file_obj)

            except Exception as error_when_writing:
                written = [False, "Error {} When Writing.".format(error_when_writing)]
                self.logger.error("Unable to Write Audit {} with Error {}".format(self.source_key, error_when_writing))
            else:
                self.logger.debug("Write File for {} to {}".format(self.source_key, audit_file))
                written = [True, "File written to {}".format(audit_file)]

        return written
