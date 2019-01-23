#!/bin/bash

#
# FPM Build Script
#
# Should use FPM to build the package.
#

#current_branch=$(git rev-parse --abbrev-ref HEAD)
#last_tag=$(git tag --merged ${current_branch})

echo -e "Moved to manowar_agent repository."

#if [[ -z ${TRAVIS_TAG} ]] ; then
    # I'm not Building a Tag as the var doesn't exist
    # So treat this as a build from the last tag
#    VERSION=${last_tag:=0\.0}.${TRAVIS_BUILD_NUMBER}
#else:
#    VERSION=${TRAVIS_TAG}

# Build Saltcell Pip

#export SALTCELL_VERSION=${VERSION}

#./setup.py sdist bdist_wheel
