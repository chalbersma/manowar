#!/bin/bash

# Here be pre-build steps if needed

echo -e "MariaDB Things"

sudo apt-get install software-properties-common
sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xF1656F24C74CD1D8
sudo add-apt-repository 'deb [arch=amd64,arm64,i386,ppc64el] http://nyc2.mirrors.digitalocean.com/mariadb/repo/10.3/ubuntu xenial main'

# Make Clean Docs
rm -rf docs/

mkdir docs

# Var Debug Findings
echo -e "TRAVIS_PULL_REQUEST_BRANCH : ${TRAVIS_PULL_REQUEST_BRANCH}"
echo -e "TRAVIS_PULL_REQUEST_SLUG : ${TRAVIS_PULL_REQUEST_SLUG}"
echo -e "TRAVIS_REPO_SLUG : ${TRAVIS_REPO_SLUG}"
echo -e "TRAVIS_BRANCH : ${TRAVIS_BRANCH}"
echo -e "TRAVIS_EVENT_TYPE : ${TRAVIS_EVENT_TYPE}"
echo -e "Git Branch : $(git rev-parse --abbrev-ref HEAD)"
