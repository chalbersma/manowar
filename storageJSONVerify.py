#! /usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# Parsing Argument
import argparse
# System Operations
import sys
# Import Schema Parser
# Requires python3-jsonschema installed
import jsonschema
# Import
import json
# Import
import os

JSONSCHEMA_FILEPATH="/oc/local/secops/jellyfish2/"
JSONSCHEMA_DEFAULT_SCHEMA=JSONSCHEMA_FILEPATH+"/jellyfish_storage.json.schema"


if __name__ == "__main__":
	parser = argparse.ArgumentParser()

	# -h help
	# -s Audit Definitions (Required)
	# -j JSON File

	parser.add_argument("-s", "--schema", help="JSON Schema File to use for validation. (Default : jellyfish_storage.json.schema)", default=JSONSCHEMA_DEFAULT_SCHEMA )
	parser.add_argument("-j", "--json", help="JSON File to Validate", required="TRUE")

	args=parser.parse_args()

	schema_file=args.schema
	json_file=args.json

def storageJSONVerify(schema_file, json_file):

	if type(json_file) is dict:
		# Treat this as the dict itself
		this_json = json_file
	else:
		try:
			with open(json_file,"r") as this_json_file:
				this_json = json.load(this_json_file)
		except ValueError as err:
			msg="Error in the Format of your JSON File " + err
			return (False, msg)

	#print(this_json)

	if type(schema_file) is dict :
		# Treat this as the schema itself
		this_schema = schema_file
	else:
		try:
			with open(schema_file,"r") as this_schema_file:
				this_schema = json.load(this_schema_file)
		except ValueError as err:
			msg="Error in the Format of your Schema File: " + str(err)
			return (False, msg)


	#print(this_schema)

	try:
		jsonschema.validate(this_json,this_schema)
	except jsonschema.exceptions.ValidationError as err:
		msg="Error in your JSON File: " + err
		return (False, msg)
	except jsonschema.exceptions.SchemaError as err:
		msg="Error with your Schema File: " + err
		return (False, msg)
	else:
		msg="JSON file passed Schema Validation."
		return (True, msg)

if __name__ == "__main__":
	#"We're going to run the main stuff
	result = storageJSONVerify(schema_file, json_file)

	print(result)
