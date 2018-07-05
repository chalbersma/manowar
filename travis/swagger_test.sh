#!/bin/bash

set -x

# Test each file in the api to ensure it has a valid swagger definition.

./pull_swagger.py -d jelly_api_2/ -C

isGud=$?

if [[ ${isGud} -eq 1 ]] ; then
  # It Aien't Gud
  echo -e "Pull Swagger jelly_api_2. Not all audits have definitions"
  exit 1
fi

exit 0
