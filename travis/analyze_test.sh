#!/bin/bash

set -x

# Run Scheduler Test
# TO Speed things up -n 14 grabs only audits from the last 14 days.
./manowar_server -vvv -c travis/artifacts/manoward.yaml analyze -a travis/artifacts/audits.d  -n 14

analyze_good=$?

if [[ ${analyze_good} -eq 0 ]] ; then
	# Analyze Worked, let's try to collate
	# Collate Here
	./manowar_server -vvv -c travis/artifacts/manoward.yaml collate

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

