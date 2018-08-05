#!/bin/bash

# Here be pre-build steps if needed

echo -e 'Pre Steps'

echo -e "Enabling Trusty Backports for Shellcheck"

echo -e "deb http://archive.ubuntu.com/ubuntu trusty-backports main restricted universe multiverse" | sudo tee /etc/apt/sources.list.d/backports.list

echo -e "Enabling Mariadb 10.2 Repo"

sudo apt-get install software-properties-common

sudo apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xcbcb082a1bb943db

sudo add-apt-repository 'deb [arch=amd64] http://sfo1.mirrors.digitalocean.com/mariadb/repo/10.2/ubuntu trusty main'

sudo apt-get update

# Make Clean Docs
rm -rf docs/

mkdir docs

# Var Debug Findings
echo -e "TRAVIS_PULL_REQUEST_BRANCH : ${TRAVIS_PULL_REQUEST_BRANCH}"
echo -e "TRAVIS_PULL_REQUEST_SLUG : ${TRAVIS_PULL_REQUEST_SLUG}"
echo -e "TRAVIS_REPO_SLUG : ${TRAVIS_REPO_SLUG}"
