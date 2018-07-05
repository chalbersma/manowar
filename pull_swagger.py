#!/usr/bin/env python3

'''
Copyright 2018, VDMS
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
import jinja2
import json
import sys

if __name__ == "__main__" :

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--apiDirectory", help="API Directory to recurse through", required=True)
    parser.add_argument("-o", "--outputfile", help="File to output the swagger doc to")
    parser.add_argument("-t", "--template", help="Jinja Template to use for output")
    parser.add_argument("-C", "--checkonly", action="store_true", help="Check to ensure every file in api has definition")

    args = parser.parse_args()

    if args.apiDirectory[-1] == "/" :
        APIDIR=args.apiDirectory[0:-1]
    else :
        APIDIR=args.apiDirectory


    if args.checkonly :
        CHECKONLY = True
    else :
        CHECKONLY = False

    if args.outputfile  :
        OUTFILE = args.outputfile

    if args.template :
        TEMPLATE = args.template


def generateSwaggerPieces(apiDirectory):
    api_endpoint_files = []
    swagger_pieces = dict()
    swagger_pieces["data"] = list()
    swagger_pieces["undoc"] = list()


    for (dirpath, dirnames, filenames) in os.walk(apiDirectory) :
        for singlefile in filenames :
            onefile = dirpath + "/" + singlefile
            if singlefile.find(".py", -3) > 0 :
                api_endpoint_files.append(onefile)

    swagger_pieces["files"] = api_endpoint_files


    for this_file in api_endpoint_files :
        with open(this_file) as this_file_object:
            this_file_parsed = ast.parse("".join(this_file_object).strip('\n'))
            this_docstring = ast.get_docstring(this_file_parsed)
            #print(this_file, type(this_docstring))
            ## Check if there is a docstring (If none it will be None)
            if type(this_docstring) is str :
                #print(this_docstring)
                ## Now Grab just the Swagger ##
                this_swagger_match = re.search("\`\`\`swagger-yaml(.+)\`\`\`", this_docstring, re.DOTALL)
                #print(this_swagger_match)
                if this_swagger_match is not None :
                    #print("String Here")
                    this_swagger_string = this_swagger_match.group(1)
                    swagger_pieces["data"].append( { "filename" : this_file, \
                                 "text" : this_swagger_string })
                else:
                    swagger_pieces["undoc"].append(this_file)
            else :
                # Ignore `__init__.py`
                isinitpy = re.search("__init__\.py$", this_file)
                if isinitpy is not None :
                    # Ignore this file
                    pass
                else:
                    # It's not the init.py
                    swagger_pieces["undoc"].append(this_file)

    return swagger_pieces

def generateOutputFile(swaggerPieces, outputfile, templatefile) :

    with open(templatefile) as templatefile_object :
        template_file_parsed = templatefile_object.read()

    jinja_template = jinja2.Template(template_file_parsed)

    rendered_swagger = jinja_template.render(swagger_pieces=swaggerPieces)

    with open(outputfile, 'w') as swaggerfile_object :
        swaggerfile_object.write(rendered_swagger + '\n')

if __name__ == "__main__" :
    swaggerPieces = generateSwaggerPieces(APIDIR)

    if CHECKONLY == True :
        # Do Check
        if len(swaggerPieces["undoc"]) > 0 :
            # Problems
            print("Check Failure: Found undocumented endpoints!")
            print(swaggerPieces["undoc"])
            sys.exit(1)
        else:
            print("Check OK: No Undocumented Endpoints Found")
            sys.exit(0)
        #print(json.dumps(swaggerPieces))
    else :
        # Do Generate
        generateOutputFile(swaggerPieces["data"], OUTFILE, TEMPLATE)
