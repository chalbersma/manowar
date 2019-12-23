#!/usr/bin/env python3

import argparse
import os
import os.path
import logging
import re
import json

import feedparser
import pyjq

import audittools.audits_usn


_known_feeds = {"usn" : {"url" : "https://usn.ubuntu.com/usn/atom.xml",
                         "subdir" : "ubuntu_usn",
                         "jq_obj_source_key" : ".title",
                         "regex_obj_source_key" : r"(USN-\d{1,4}-\d{1,2})",
                         "update_existing" : False,
                         "audit_source_obj" : audittools.audits_usn.AuditSourceUSN,
                         "format" : "json"
                        }
               }


if __name__ == "__main__" :
    parser = argparse.ArgumentParser()
    #parser.add_argument("-v", "--verbose", action='store_true', help="Turn on Verbosity")
    parser.add_argument("-v", "--verbose", action='append_const', help="Turn on Verbosity", const=1, default=[])
    parser.add_argument("-b", "--basedir", default=os.getcwd())
    parser.add_argument("-f", "--feed", required=True)
    parser.add_argument("-C", "--confirm", action="store_true", default=False)
    parser.add_argument("-m", "--max", type=int, default=5)

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

    LOGGER = logging.getLogger("audits_usn.py")

    LOGGER.debug("Welcome to Audits RSS Creator.")

    FEED = args.feed
    CONFIRM = args.confirm
    MAX = args.max

    BASEDIR = args.basedir

    if FEED not in _known_feeds.keys():
        LOGGER.error("Unknown Feed Definition : {}".format(FEED))
        LOGGER.info("Currently Known Feeds {}".format(",".join(_known_feeds.keys())))
        sys.exit(1)

def feed_create(feed_name, feed_config=None, basedir=None, confirm=False, max_audit=5):

    '''
    Using the Configuration Specified, Query the RSS Feed and Create Audits for Missing
    Entries.
    '''

    logger = logging.getLogger("rss_creator.py:feed_create")

    audit_source_items = dict()

    if feed_config is None:
        logger.debug("Feed Config Not Given, Choosing {} from Global Config.".format(feed_name))
        feed_config = _known_feeds[feed_name]

    this_path = os.path.join(basedir, feed_config.get("subdir", feed_name))

    if os.path.isdir(basedir) is False:
        # Base Directory Exists
        logger.error("Base Path of {} Doesn't Exist.")

        raise FileNotFoundError("Base Path Missing")

    if os.path.isdir(this_path) is False:

        logger.warning("Subdirectory doesn't exist attempting to Create")

        try:
            os.mkdir(this_path)
        except Exception as subdir_error:
            logger.error("Error when creating subdirectory : {}".format(subdir_error))

            raise subdir_error

    # I have a valid place to Put my Stuff. Let's Grab my URL
    try:
        feed_obj = feedparser.parse(feed_config["url"])
    except Exception as feed_read_error:
        logger.error("Unable to Read RSS Feed Returning Empty")
        feed_obj = {"entries" : list()}


    if len(feed_obj["entries"]) == 0:
        logger.warning("No Entries in Given URL.")
    else:
        # Have Entries Let's give this a whirl
        current_num = 0

        for entry in feed_obj["entries"]:
            current_num = current_num + 1

            best_source_key = None

            if "jq_obj_source_key" in feed_config.keys():
                # I have JQ to Try
                jq_result = pyjq.one(feed_config["jq_obj_source_key"], entry)

                if jq_result is not None:
                    best_source_key = jq_result

            logger.debug("Best Source key After JQ : {}".format(best_source_key))

            if "regex_obj_source_key" in feed_config.keys():

                regex_result = re.search(feed_config["regex_obj_source_key"], str(best_source_key), re.I)

                if regex_result is not None:
                    best_source_key = regex_result.group(1)

            logger.debug("Best Source key After Regex : {}".format(best_source_key))



            if best_source_key is not None and len(best_source_key) > 0:

                as_kwargs = {"source_key" : best_source_key,
                             "audit_filename" : "{}.{}".format(best_source_key, feed_config["format"]),
                             "audit_path" : this_path
                            }

                as_args = list()

                as_obj = feed_config["audit_source_obj"](*as_args, **as_kwargs)

                if as_obj.validate_audit_live() is True:

                    # See if File Exists
                    if as_obj.audit_file_exists() is False:
                        # Add to Object
                        if confirm is False:
                            logger.info("Audit {} File Not Written to {} Confirm not Set.".format(best_source_key, as_obj.audit_filename))
                            audit_source_items[best_source_key] = ["False", "Confirm not Set"]
                        else:
                            logger.info("Audit {} Writing to {}.".format(best_source_key, as_obj.audit_filename))

                            audit_source_items[best_source_key] = as_obj.write_audit(file_format=feed_config["format"])
                    else:
                        logger.info("Audit File {} Has existing File.".format(best_source_key))
                        audit_source_items[best_source_key] = [False, "Pre-Existing File."]
                else:
                    logger.warning("Audit Finding for Source {} Not Valid.".format(best_source_key))
                    audit_source_items[best_source_key] = [False, "Invalid Audit on Creation"]

            else:
                logger.warning("No Source Key found for Entry : {}".format(entry["id"]))



            if max_audit is not None and max_audit != -1 and current_num > (max_audit - 1):
                logger.info("Reached Maximum of {} Audits Processed.".format(current_num))
                break

    return audit_source_items

if __name__ == "__main__" :

    # Run the Thing
    results = feed_create(FEED, basedir=BASEDIR, confirm=CONFIRM, max_audit=MAX)

    print(json.dumps(results, indent=2))
