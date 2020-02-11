#!/bin/bash

# Bandit Checks

# Encoding Check

################### Python Checks #####################################
# ./jelly_api & ./jelly_display are the older versions of
# this project. They do not and should evaluated and are
# there only in case something needs to be turned back on.
python_files=$(find . -type d -wholename ./lib -prune -o \
                    -type f -regex ".*\.py$")

bandit_failure="pass"
pylint_failure="pass"
for file in ${python_files} ; do
  this_temp=$(mktemp /tmp/banditout.XXXXX)
  # -ll -ii get's medium confidence medium severity findings and above
  bandit -ll -ii "${file}" > "${this_temp}"
  this_file_good=$?
  if [[ ${this_file_good} -gt 0 ]] ; then
    echo -e "BANDIT: ${file} had issues please investigate."
    cat "${this_temp}"
    bandit_failure="fail"
  else
    echo -e "BANDIT: ${file} good."
  fi

done

if [[ $bandit_failure == "fail" ]] ; then
  echo -e "Bandit Failures Detected"
  exit 1
else
  echo -e "Bandit Checks Passed"
fi

if [[ $pylint_failure == "fail" ]] ; then
  echo -e "Pylint Failures Detected"
  exit 1
else
  echo -e "Pylint Checks Passed"
fi

bash_files=$(find . -type d -wholename ./lib -prune -o \
             -type d -wholename ./setup -prune -o \
             -type d -prune -o \
             -type f -regex ".*\.sh$")

################### Bash Checks ######################################
for file in ${bash_files} ; do
  shellcheck "${file}"

  was_shellcheck_good=$?

  if [[ ${was_shellcheck_good} -gt 0 ]] ; then
    echo -e "SHELLCHECK: ${file} had issues please investigate."
    #exit 1
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

