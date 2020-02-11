#!/bin/bash

set -x

# Run Scheduler Test
./manowar_server -vvv -c travis/artifacts/manoward.yaml analyze -a travis/artifacts/audits.d 

analyze_good=$?

if [[ ${analyze_good} -eq 0 ]] ; then
	# Analyze Worked, let's try to collate
	# Collate Here
	./manowar_server -vvv -c travis/artifacts/manoward.yaml collate -vvv

	collate_good=$?

	if [[ ${collate_good} -eq 0 ]] ; then
		echo -e "Run_analyze Simulation Worked."
	else
		echo -e "Analyze Worked but Collate Failed."
		exit 1

	fi
else
	echo -e "Analyze Failed, please check logs"
	exit 1
fi

