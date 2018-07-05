#!/bin/bash

# Bandit Checks

# Encoding Check

################### Python Checks #####################################
# ./jelly_api & ./jelly_display are the older versions of
# this project. They do not and should evaluated and are
# there only in case something needs to be turned back on.
python_files=$(find . -type d  -wholename ./jelly_api -prune -o \
                    -type d -wholename ./jelly_display -prune -o \
                    -type f -regex ".*\.py$")

for file in ${python_files} ; do
  this_temp=$(mktemp /tmp/banditout.XXXXX)
  bandit "${file}" > "${this_temp}"
  if [[ $? -gt 0 ]] ; then
    echo -e "BANDIT: ${file} had issues please investigate."
    cat "${this_temp}"
    exit 1
  else
    echo -e "BANDIT: ${file} good."
  fi

  # Get bandit working first

  #pylint3 ${file}
  #if [[ $? -gt 0 ]] ; then
  #  echo -e "PYLINT:: ${file} had issues please investigate."
  #  exit 1
  #fi

done

bash_files=$(find -type f -regex ".*\.sh$")

################### Bash Checks ######################################
for file in ${bash_files} ; do
  shellcheck "${file}"

  if [[ $? -gt 0 ]] ; then
    echo -e "SHELLCHECK: ${file} had issues please investigate."
    exit 1
  else
    echo -e "SHELLCHECK: ${file} Good."
  fi

done

## Check Documentation
mdl -s travis/artifacts/mdl_style source_docs

style_check_success=$?

if [[ ${style_check_success} -gt 0 ]] ; then
	echo -e "Markdown Style Failed"
	exit 1
else
	echo -e "Markdown Style Passed"
fi

