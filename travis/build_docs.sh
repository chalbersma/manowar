#!/bin/bash

# Build the Docs
set -x

git config user.email "automateduser@example.com"
git config user.name "Travis"
git config push.default matching

# Diagrams
mkdir ./source_docs/plantuml
cp /home/travis/plantuml/* ./source_docs/plantuml/

populate_diag=$?

if [[ ${populate_diag} -gt 0 ]] ; then
    echo -e "Error populating Diagrams"
    #exit 1
fi

# Do MkDocs
mkdocs --version
mkdocs build
mkdocs build --clean

echo ${TRAVIS_BRANCH}
echo ${TRAVIS_REPO_SLUG}
echo ${TRAVIS_EVENT_TYPE}

if [[ ${TRAVIS_BRANCH} == "master" && ${TRAVIS_PULL_REQUEST_BRANCH} == "staging" 
      && ${TRAVIS_REPO_SLUG} == "chalbersma/manowar" && ${TRAVIS_EVENT_TYPE} == "pull_request" ]] ; then

  echo -e "Vars: ${TRAVIS_PULL_REQUEST_BRANCH} -> ${TRAVIS_BRANCH} in ${TRAVIS_PULL_REQUEST_SLUG} type ${TRAVIS_EVENT_TYPE}"

  # Pull request is from staging into master; the "blessed path"
  echo -e 'Pull is from Staging to Master, generating latest documentation.'

  # Only if it's in the right shall I push.
  mkdocs gh-deploy
  
  #git commit -m "[ci skip] Travis is updating the documentation; build no.: ${TRAVIS_BUILD_NUMBER}"
  #git push

else

  echo -e "Vars: ${TRAVIS_PULL_REQUEST_BRANCH} -> ${TRAVIS_BRANCH} in ${TRAVIS_PULL_REQUEST_SLUG} type ${TRAVIS_EVENT_TYPE}"

  # Pull request is not blessed
  echo -e 'Non staging to master pull request not generating docs.'

fi
