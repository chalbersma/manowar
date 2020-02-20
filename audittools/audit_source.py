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
import uuid

import yaml
import packaging.version

import manoward

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

        self.overwrite_strategy = kwargs.get("overwrite", "no")

        self.audit_data = {"vuln-name" : kwargs.get("vuln-name", None),
                           "vuln-primary-link" : kwargs.get("vuln-primary-link", None),
                           "vuln-priority" : kwargs.get("vuln-priority", None),
                           "vuln-additional-links" : kwargs.get("vuln-additional-links", dict()),
                           "vuln-long-description" : kwargs.get("vuln-long-description", None),
                           "vuln-short-description" : kwargs.get("vuln-short-description", None),
                           "comparisons" : kwargs.get("comparisons", dict()),
                           "filters" : kwargs.get("filters", dict()),
                           "jellyfishversion" : kwargs.get("jellyfishversion", "2.6")}

        self.audit_uuid = kwargs.get("audit_uuid", str(uuid.uuid4()))
        self.audit_id = kwargs.get("audit_id", None)

        self.audit_data["filename"] = kwargs.get("filename", "nofile")

        self.audit_data["auditts"] = kwargs.get("auditts", 1)

        if kwargs.get("do_db", False):
            self.db_load(kwargs["db_cur"])

    def __str__(self):
        """
        String Representation of the Thing
        """

        return "Source:{} Name:{} Priority:{} Version:{}".format(self.source_key,
                                                                 self.audit_name,
                                                                 self.audit_data["vuln-priority"],
                                                                 self.audit_data["jellyfishversion"])

    def db_load(self, db_cur):

        """
        Use the Database to Load a DB Object for Usage
        """

        if self.audit_id is None:
            get_query = '''select * from audits where audit_uuid = %s'''
            query_args = [self.audit_uuid]
        else:
            get_query = '''select * from audits where audit_id = %s'''
            query_args = [self.audit_id]

        run_result = manoward.run_query(db_cur,
                                        get_query,
                                        args=query_args,
                                        do_abort=False,
                                        one=True,
                                        require_results=True)

        if run_result["has_error"] is True:
            self.logger.error("Attempting to Load from DB {} or {} (first). None Found".format(audit_id, self.audit_uuid))
            raise ValueError()
        else:
            this_data = run_result.get("data", dict())

            self.source_key = this_data["audit_name"]
            self.audit_name = this_data["audit_name"]

            self.audit_filename = this_data["filename"]

            self.audit_data = {"vuln-name": this_data["audit_name"],
                               "vuln-primary-link": this_data["audit_primary_link"],
                               "vuln-priority": this_data["audit_priority"],
                               "vuln-additional-links": json.loads(this_data["audit_secondary_links"]),
                               "vuln-long-description": this_data["audit_long_description"],
                               "vuln-short-description": this_data["audit_short_description"],
                               "comparisons": json.loads(this_data["audit_comparison"]),
                               "filters": json.loads(this_data["audit_filters"]),
                               "jellyfishversion": this_data["audit_version"],
                               "filename" : this_data["filename"]}

            self.audit_uuid = this_data["audit_uuid"]

            self.audit_data["auditts"] = int(this_data["audit_ts"].timestamp())
            self.audit_id = this_data["audit_id"]

        return self.audit_uuid

    def buckets(self):

        """
        Return all the matching Buckets in A List
        """

        buckets = [bucket for bucket in self.audit_data["comparisons"].keys() if bucket in self.audit_data["filters"].keys()]

        return buckets

    def update_db(self, db_cur, **kwargs):

        """
        Updates the Database Entry for this Audit
        """

        written = False
        my_id = None
        message = "Write not Attempted"

        if self.validate_audit_live() is False:
            self.logger.error("Unable to Validate Audit {} Not Writing to Database.")
            message = "Audit Failed Validation Precheck. Not Recording to Database."
        else:

            # Let's attempt to Update Write
            replace_sql = '''INSERT INTO audits  
                             (audit_name, audit_uuid,
                             audit_priority, 
                             audit_short_description, audit_long_description,
                             audit_primary_link, audit_secondary_links, 
                             audit_filters, 
                             audit_comparison,
                             filename, 
                             audit_version, audit_ts
                             )
                             VALUES ( %s, %s, 
                             %s,
                             %s, %s,
                             %s, %s, 
                             %s, 
                             %s,
                             %s, 
                             %s, FROM_UNIXTIME(%s))
                             on DUPLICATE KEY UPDATE
                             audit_priority = %s,
                             audit_short_description = %s, audit_long_description = %s,
                             audit_primary_link = %s, audit_secondary_links = %s,
                             audit_filters = %s, 
                             audit_comparison = %s,
                             filename = %s,
                             audit_version = %s, audit_ts = FROM_UNIXTIME(%s)
                             '''

            replace_args = [self.audit_name, self.audit_uuid,
                            self.audit_data["vuln-priority"],
                            self.audit_data["vuln-short-description"][:254], self.audit_data["vuln-long-description"],
                            self.audit_data["vuln-primary-link"], json.dumps(self.audit_data["vuln-additional-links"], sort_keys=True),
                            json.dumps(self.audit_data["filters"], sort_keys=True),
                            json.dumps(self.audit_data["comparisons"], sort_keys=True),
                            self.audit_data["filename"],
                            self.audit_data["jellyfishversion"], self.audit_data["auditts"],
                            self.audit_data["vuln-priority"],
                            self.audit_data["vuln-short-description"][:254], self.audit_data["vuln-long-description"],
                            self.audit_data["vuln-primary-link"], json.dumps(self.audit_data["vuln-additional-links"], sort_keys=True),
                            json.dumps(self.audit_data["filters"], sort_keys=True),
                            json.dumps(self.audit_data["comparisons"], sort_keys=True),
                            self.audit_data["filename"],
                            self.audit_data["jellyfishversion"], self.audit_data["auditts"]]

            run_result = manoward.run_query(db_cur,
                                            replace_sql,
                                            args=replace_args,
                                            do_abort=False,
                                            lastid=True,
                                            require_results=False)

            if run_result["has_error"] is True:
                message = "Error When trying to Update Audit Info from file {}".format(self.audit_data["filename"])
                raise ValueError()
            elif isinstance(run_result.get("data", None), int) is False:
                message = "Ran Query But unable to Get Audit ID, Likely an Update"
                ## TODO Make Mariadb 10.5 with RETURNING as a requirement
                written = True
                my_id = -1
            else:
                my_id = run_result["data"]
                written = True
                message = "Wrote Audit {} to ID {}".format(self.audit_name, my_id)
                self.audit_id = my_id

        return dict(written=written, wid=my_id, message=message)



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

        if self.overwrite_strategy == "yes":
            self.logger.debug("Overwrite is set to yes. Always overwriting.")
        else:
            if os.path.isfile(audit_file) is True:
                if self.overwrite_strategy == "newer":
                    self.logger.debug("Checking Existing File for Newness")
                    try:
                        with open(audit_file, "r") as existing_audit_file:
                            newer = False
                            existing_audit_data = json.load(existing_audit_file)[self.source_key]

                            existing_ts = existing_audit_data.get("auditts", 0)
                            existing_ver = packaging.version.parse(str(existing_audit_data.get("jellyfishversion", "0.0")))
                            new_ver = packaging.version.parse(str(self.audit_data.get("jellyfishversion", "0.0")))

                            if self.audit_data.get("auditts", 0) > existing_ts:
                                self.logger.info("Overwriting Audit As Existing TS is older than New TS")
                                self.logger.debug("{} > {}".format(self.audit_data.get("auditts", 0), existing_ts))
                                newer = True

                            if new_ver > existing_ver:
                                self.logger.info("Overwriting Audit As Existing Audit Version is older than New Audit Version")
                                self.logger.debug("{} > {}".format(existing_ver, new_ver))
                                newer = True

                            if newer is False:
                                exists = True
                    except:
                        self.logger.warning("Unable to Read File as Expected. I'm not going to attempt an overwrite.")
                        exists = True
                else:
                    # All other overwrite Strategies got to the default, ignore if no new.
                    self.logger.debug("Existing File Not Overwriting")
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
