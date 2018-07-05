#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# Line below is Nosec'ed because lxml is in the standard library and the suggested
# Script isn't. To reach the widest range we want to use python3 libraries that
# are in the standard library
from lxml import html #nosec

# Function that takes a CVE # and pulls information about it down
# From Ubuntu's site.
import argparse
import requests
import re
import json

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("cve", help="CVE To Check")
    parser.add_argument("-V", "--verbose", action='store_true', help="Verbose Mode Show more Stuff")
    parser._optionals.title = "DESCRIPTION "

    # Parser Args
    args = parser.parse_args()
    CVE=args.cve

    if CVE == False :
        print("CVE Required")

    if args.verbose :
        VERBOSE=True
    else :
        VERBOSE=False

def shuttlefish(cve, verbose=False) :

    # Parse CVE
    #
    REGEX_MATCH=r"[C,c][V,v][E,e]-(\d+)-(\d+)"

    matches = re.match(REGEX_MATCH, cve)

    try:
        cve_year = matches.group(1)
        cve_number = matches.group(2)
    except AttributeError as E :
        # None Found
        if verbose == True :
            print("Not a CVE")
        return False
    else :
        # We've successfully parsed the CVE
        cve_url = "https://people.canonical.com/~ubuntu-security/cve/{}/CVE-{}-{}.html".format(cve_year, cve_year, cve_number)

        response = requests.get(cve_url)

        text_response = response.text

        cve_full_page = html.fromstring(text_response)

        cve_dict = dict()
        cve_dict["references"] = list()

        h2s = cve_full_page.cssselect("h2")

        for item in range(0, len(h2s)) :
            # Title
            cve_dict["title"] = h2s[item].text_content()

        page_items = cve_full_page.cssselect("div[class=item]")

        for page_item_index in range(0, len(page_items)) :

            this_content = page_items[page_item_index].text_content()
            priority_match = re.match("^Priority (.*)$", this_content)
            if priority_match != None :
                cve_dict["priority"] = priority_match.group(1)

            description_match = re.match("^Description (.*)$", this_content)
            if description_match != None :
                cve_dict["description"] = description_match.group(1)

            ubuntu_description_match = re.match("^Ubuntu-Description (.*)$", this_content)
            if ubuntu_description_match != None :
                cve_dict["ubuntu_description"] = ubuntu_description_match.group(1)

            references_match = re.match("^References (.*)$", this_content)
            if references_match != None :
                full_references = references_match.group(1)
                link_splits = re.split("(http)", full_references)
                for i in range(1, len(link_splits), 2) :
                    # First line is useless, Want to combine 2 Items
                    this_link = link_splits[i] + link_splits[i+1]

                    cve_dict["references"].append(this_link)

        pkg_items = cve_full_page.cssselect("div[class=pkg]")

        pkg_dict = dict()

        for pkg_item_index in range(0, len(pkg_items)) :

            this_pkg_dict = dict()

            this_raw_content = pkg_items[pkg_item_index].text_content()

            this_content = [ content for content in this_raw_content.split("\n") if len(content) > 0 ]

            pkg_name_match = re.match("^PackageSource: (.*) \(", this_content[0])
            if pkg_name_match != None :
                this_pkg_name = pkg_name_match.group(1)
                this_pkg_dict["package_name"] = this_pkg_name

            upstream_status_match = re.match("^Upstream:(.*)$", this_content[1])
            if upstream_status_match != None :
                this_upstream_status = upstream_status_match.group(1)
                this_pkg_dict["package_upstream_status"] = this_upstream_status

            this_pkg_dict["releases"] = dict()

            for released_index in range(2, len(this_content)) :
                this_line = this_content[released_index]

                pkg_release_status_match = re.match("Ubuntu \d\d\.\d\d[a-zA-Z ]{0,5}\(([a-zA-Z]+) [a-zA-Z]+\)\:(.*)$", this_line)

                if pkg_release_status_match != None :
                    ubuntu_release = pkg_release_status_match.group(1).lower()
                    release_status = pkg_release_status_match.group(2).lower()

                    if release_status in [ "released" ] :
                        version = this_content[released_index+1].strip('\(\)')
                    else:
                        version = False

                    this_release_dict = { "release" : ubuntu_release,
                      "status" : release_status,
                      "version" : version }

                    this_pkg_dict["releases"][ubuntu_release] = this_release_dict


            if this_pkg_name != None :
                pkg_dict[this_pkg_name] = this_pkg_dict

        cve_dict["packages"] = pkg_dict


    return cve_dict

if __name__ == "__main__" :

    cve_data = shuttlefish(cve=CVE, verbose=VERBOSE)

    print(json.dumps(cve_data))
