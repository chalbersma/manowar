#!/bin/bash

set -x


swagger_ui_version="3.9.0"
swagger_tar_file="https://github.com/swagger-api/swagger-ui/archive/v${swagger_ui_version}.tar.gz"

mkdir /home/travis/swagger

# Download Swagger UI
wget "${swagger_tar_file}" -O /home/travis/swagger.tar.gz

swagger_ui_download_good=$?

if [[ ${swagger_ui_download_good} -gt 0 ]] ; then
	# Couldn't Download
	echo -e "Can't Download Swagger UI"
	exit 1
fi

# Extract Swagger UI
tar -xvzf /home/travis/swagger.tar.gz --strip 1 -C /home/travis/swagger/

swagger_extract_good=$?

if [[ ${swagger_extract_good} -gt 0 ]] ; then
	echo -e "Swagger Extraction Didn't Work"
	exit 1
fi

# Do Swagger Build
./pull_swagger.py -d ./jelly_api_2/ -t ./openapi3/openapi3.yml.jinja -o /home/travis/jellyfish_swagger.yaml

swagger_build_status=$?

if [[ ${swagger_build_status} -gt 0 ]]; then
	# Fail the Build
	echo -e "Failure to build swagger file"
	exit 1
fi

# Copy Swagger into dist
cp /home/travis/jellyfish_swagger.yaml /home/travis/swagger/dist/

sed -i -e 's/http\:\/\/petstore.swagger\.io\/v2\/swagger\.json/jellyfish_swagger.yaml/g' /home/travis/swagger/dist/index.html

replace_swagger=$?

if [[ ${replace_swagger} -gt 0 ]] ; then
	echo -e "Swagger Replace Failed"
	exit 1
fi




