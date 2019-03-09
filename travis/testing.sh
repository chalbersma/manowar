#!/bin/bash

# Bandit Checks

# Encoding Check

################### Python Checks #####################################
python_files=$(find . -type f -regex ".*\.py$")

for file in ${python_files} ; do
  this_temp=$(mktemp /tmp/banditout.XXXXX)
  bandit "${file}" > "${this_temp}"
  this_file_good=$?
  if [[ ${this_file_good} -gt 0 ]] ; then
    echo -e "BANDIT: ${file} had issues please investigate."
    cat "${this_temp}"
    exit 1
  else
    echo -e "BANDIT: ${file} good."
  fi

  # Get bandit working first

  pylint3 ${file}
  if [[ $? -gt 0 ]] ; then
    echo -e "PYLINT:: ${file} had issues please investigate."
  fi

done

bash_files=$(find . -type f -regex ".*\.sh$")

################### Bash Checks ######################################
for file in ${bash_files} ; do
  shellcheck "${file}"

  was_shellcheck_good=$?

  if [[ ${was_shellcheck_good} -gt 0 ]] ; then
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

