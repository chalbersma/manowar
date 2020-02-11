#!/bin/bash

set -x

./manowar_server -vv swagger -d ./jelly_api_2/ -t ./openapi3/openapi3.yml.jinja -o ~/tmp/swagger.json

swagger_build_status=$?

if [[ ${swagger_build_status} -gt 0 ]]; then
	# Fail the Build
	echo -e "Failure to build swagger file"
	exit 1
fi

#git add -- ./manoward/static/sw/swagger.json





