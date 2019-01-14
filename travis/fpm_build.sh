#!/bin/bash

#
# FPM Build Script
#
# Should use FPM to build the package.
#

current_branch=$(git rev-parse --abbrev-ref HEAD)
last_tag=$(git tag --merged ${current_branch})

if [[ -z ${TRAVIS_TAG} ]] ; then
    # I'm not Building a Tag as the var doesn't exist
    # So treat this as a build from the last tag
    VERSION=${last_tag:=0\.0}.${TRAVIS_BUILD_NUMBER}
else:
    VERSION=${TRAVIS_TAG}

# Build Deb
fpm -s virtualenv -t deb\
  --license BSD \
  --maintainer chris+manowar@halbersma.us \
  --url https://chalbersma.github.io/manowar/ \
  --description "Saltstack based collection agent for hosts." \
  --architecture x86_64 \
  --category utilities \
  -n manowar-stingcell -v ${VERSION} \
  --prefix /opt/stingcell \
  requirements.txt
