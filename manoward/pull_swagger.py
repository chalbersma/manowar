#!/usr/bin/env python3

'''
Copyright 2018, 2020 VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

pull_swagger.py

Do this: 
`./pull_swagger.py -d jelly_api_2 -t ~/Documents/src/svn_ec/secops/jellyfish2/swagger/api.yaml.jinja -o ~/gitch/secops/static/swagger/jellyfish-swagger.yaml`
(Replacing the `~/Documents/s...` and `~/gitch/secops...` with the proper paths for your workstation. And then commit to repository
'''

import ast
import os
import argparse
import re
import json
import sys

import jinja2
import yaml

_host_filters = '''
- name: hostname
  in: query
  description: |
    A regex to match for the hostname. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
    regular expressions are accepted. Matched on the hostname column in the host table. With exact
    will match exactly.
  required: false
  schema:
    type: string
- name: status
  in: query
  description: |
    A regex to match for the status. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
    regular expressions are accepted. Matched on the status column in the host table. With exact
    will match exactly.
  required: false
  schema:
    type: string
- name: pop
  in: query
  description: |
    A regex to match for the pop. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
    regular expressions are accepted. Matched on the status column in the host table. With exact
    will match exactly.
  required: false
  schema:
    type: string
- name: srvtype
  in: query
  description: |
    A regex to match for the srvtype. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
    regular expressions are accepted. Matched on the status column in the host table. With exact
    will match exactly.
  required: false
  schema:
    type: string
- name: resource
  in: query
  description: |
    Matches the MOWN Resource either via Regex or Exactly (with exact). Keep in mind resources include
    the resource qualifier and resource subtype if applicable.
  required: false
  schema:
    type: string
- name: partition
  in: query
  description: |
    Matches the MOWN Parition either via Regex or Exactly.
  required: false
  schema:
    type: string
- name: service
  in: query
  description: |
    Matches the MOWN Service either via Regex or Exactly.
  required: false
  schema:
    type: string
- name: accountid
  in: query
  description: |
    Matches the MOWN Account ID either via Regex or Exactly
  required: false
  schema:
    type: string
- name: mownbase
  in: query
  description: |
    Matches the MOWN Base URI fully (with regex or Exactly). Does not include
    a matching of arguments
  required: false
  schema:
    type: string
- name: mownfull
  in: query
  description: |
    Matches the MOWN full URI fully (with regex or Exactly). Includes a Matching of Arguments
  required: false
  schema:
    type: string
- name: tagged
  in: query
  description: |
    Matches an individual tag. Returns true if the tag is defined (even if the tag is set to something
    like false). Specify using JQ style formatting. Uses the [JSON_EXISTS](https://mariadb.com/kb/en/json_exists/)
    functionality to do the JSON mapping. So **if you're looking for tag `loveit` you'd want to speicfy `$.loveit`**.
  required: false
  schema:
    type: string
  format: jsonpath
  pattern: ^\\$\\.
- name: taggedtrue
  in: query
  description: |
    Matches an individual tag. Returns true if the tag is defined as true Uses the 
    [JSON_EXTRACT](https://mariadb.com/kb/en/json_extract/)
    functionality to do the JSON mapping. So **if you're looking for tag `loveit` you'd want to speicfy `$.loveit`**.
    Will match against [true](https://mariadb.com/kb/en/true-false/), a builtin boolean. So if you specify something
    like `{"loveit" : "false"}` (Note the String not boolean) it will return true and if you have something like
    `{"zerosareawesome" : 0}` it should return false.
  required: false
  schema: 
    type: string
  format: jsonpath
  pattern: ^\\$\\."
'''

# Audit Result Filters
_ar_filters = '''
- name: bucket
  in: query
  description: |
    A regex to match for the bucket. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
    regular expressions are accepted. Matched on the status column in the audits_by_host table. With exact
    will match exactly.
  required: false
  schema:
    type: string
- name: auditResult
  in: query
  description: |
    A regex to match for the Audit Result (pass/fail). [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
    regular expressions are accepted. Matched on the audit_result column in the audit_by_host table. With exact
    will match exactly.
  required: false
  schema:
    type: string
    enum: [pass, fail, notafflicted]
- name: auditResultText
  in: query
  description: |
    A regex to match for the Audit Result Text. [PCRE](https://mariadb.com/kb/en/mariadb/regexp/) type
    regular expressions are accepted. Matched on the audit_result_text column in the audit_by_host table. With exact
    will match exactly.
  required: false
  schema:
    type: string
'''

_exact_filters = '''
- name: exact
  in: query
  description: |
    Controls your other filters and flips them from regex matches (default) to exact matches
  required: false
  schema:
    type: string
    enum: [true, false]
'''

_col_filters = '''
- name: value
  in: query
  description: |
    Value of the collection You wish to search for. Regex by Default
  required: false
  schema:
    type: string
- name: csubtype
  in: query
  description: |
    Value of the collection  subtype You wish to search for. Regex by Default
  required: false
  schema:
    type: string
'''


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--apiDirectory",
                        help="API Directory to recurse through", required=True)
    parser.add_argument("-o", "--outputfile",
                        help="File to output the swagger doc to")
    parser.add_argument("-t", "--template",
                        help="Jinja Template to use for output")
    parser.add_argument("-C", "--checkonly", action="store_true",
                        help="Check to ensure every file in api has definition")

    args = parser.parse_args()

    if args.apiDirectory[-1] == "/":
        APIDIR = args.apiDirectory[0:-1]
    else:
        APIDIR = args.apiDirectory

    if args.checkonly:
        CHECKONLY = True
    else:
        CHECKONLY = False

    if args.outputfile:
        OUTFILE = args.outputfile

    if args.template:
        TEMPLATE = args.template


def generateSwaggerPieces(apiDirectory):
    api_endpoint_files = []
    swagger_pieces = dict()
    swagger_pieces["data"] = list()
    swagger_pieces["undoc"] = list()

    for (dirpath, dirnames, filenames) in os.walk(apiDirectory):
        for singlefile in filenames:
            onefile = dirpath + "/" + singlefile
            if singlefile.find(".py", -3) > 0:
                api_endpoint_files.append(onefile)

    swagger_pieces["files"] = api_endpoint_files

    for this_file in api_endpoint_files:
        with open(this_file) as this_file_object:
            this_file_parsed = ast.parse("".join(this_file_object).strip('\n'))
            this_docstring = ast.get_docstring(this_file_parsed)
            #print(this_file, type(this_docstring))
            # Check if there is a docstring (If none it will be None)
            if type(this_docstring) is str:
                # print(this_docstring)
                ## Now Grab just the Swagger ##
                this_swagger_match = re.search(
                    "\`\`\`swagger-yaml(.+)\`\`\`", this_docstring, re.DOTALL)
                # print(this_swagger_match)
                if this_swagger_match is not None:
                    #print("String Here")
                    this_swagger_string_unhyd = this_swagger_match.group(1)
                    this_swagger_string = piece_render(
                        this_swagger_string_unhyd)
                    swagger_pieces["data"].append({"filename": this_file,
                                                   "text": this_swagger_string})
                else:
                    swagger_pieces["undoc"].append(this_file)
            else:
                # Ignore `__init__.py`
                isinitpy = re.search("__init__\.py$", this_file)
                if isinitpy is not None:
                    # Ignore this file
                    pass
                else:
                    # It's not the init.py
                    swagger_pieces["undoc"].append(this_file)

    return swagger_pieces


def piece_render(swagger_piece):
    '''
    Render an Individual API Piece. Taking into account static api endpoints
    '''

    this_template = jinja2.Template(swagger_piece)

    rendered_bit = this_template.render(hosts=_host_filters,
                                        ar=_ar_filters,
                                        exact=_exact_filters,
                                        col=_col_filters)

    # print(rendered_bit)

    return rendered_bit


def generateOutputFile(swaggerPieces, outputfile, templatefile):

    with open(templatefile) as templatefile_object:
        template_file_parsed = templatefile_object.read()

    jinja_template = jinja2.Template(template_file_parsed)

    rendered_swagger = jinja_template.render(swagger_pieces=swaggerPieces)

    swagger_json = yaml.safe_load(rendered_swagger)

    with open(outputfile, 'w') as swaggerfile_object:
        json.dump(swagger_json, swaggerfile_object, indent=2)


if __name__ == "__main__":
    swaggerPieces = generateSwaggerPieces(APIDIR)

    if CHECKONLY == True:
        # Do Check
        if len(swaggerPieces["undoc"]) > 0:
            # Problems
            print("Check Failure: Found undocumented endpoints!")
            print(swaggerPieces["undoc"])
            sys.exit(1)
        else:
            print("Check OK: No Undocumented Endpoints Found")
            sys.exit(0)
        # print(json.dumps(swaggerPieces))
    else:
        # Do Generate
        generateOutputFile(swaggerPieces["data"], OUTFILE, TEMPLATE)
