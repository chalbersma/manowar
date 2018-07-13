#!/bin/bash

# Build the Docs
set -x

git config user.email "automateduser@example.com"
git config user.name "Travis"
git config push.default matching

git branch

echo "${TRAVIS_PULL_REQUEST_BRANCH}"
echo "${TRAVIS_BRANCH}"
echo "${TRAVIS_PULL_REQUEST_SLUG}"



git branch
git checkout ${TRAVIS_BRANCH}
git branch
git pull

# Do MkDocs
mkdocs --version
mkdocs build
mkdocs build --clean

# Add Swagger Stuff
mkdir ./docs/swagger/

# Swagger
cp /home/travis/swagger/dist/* ./docs/swagger/

populate_swagger=$?

if [[ ${populate_swagger} -gt 0 ]] ; then
    echo -e "Error populating swagger"
    exit 1
fi

# Diagrams
mkdir ./docs/plantuml
cp /home/travis/plantuml/* ./docs/plantuml/

populate_diag=$?

if [[ ${populate_diag} -gt 0 ]] ; then
    echo -e "Error populating Diagrams"
    exit 1
fi

git add -- ./docs/

git status


if [[ ${TRAVIS_PULL_REQUEST_BRANCH} == "staging" && ${TRAVIS_BRANCH} == "master" && ${TRAVIS_PULL_REQUEST_SLUG} = "chalbersma/manowar" ]] ; then

  # Pull request is from staging into master; the "blessed path"
  echo -e 'Pull is from Staging to Master, generating latest documentation.'

  # Only if it's in the right shall I push.
  git commit -m "[ci skip] Travis is updating the documentation; build no.: ${TRAVIS_BUILD_NUMBER}"
  git push origin staging

else

  # Pull request is not blessed
  echo -e 'Non staging to master pull request not generating docs.'

fi
