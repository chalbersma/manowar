#!/bin/bash

set -x

./manowar_server -vvv -c travis/artifacts/manoward.yaml load -a travis/artifcats/audits.d

# Run Scheduler Test
# TO Speed things up -s a which will run audits only that have an UUID starting with a, statistically
# 1/16 of the audits loaded previously
./manowar_server -vvv -c travis/artifacts/manoward.yaml analyze -s a

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

