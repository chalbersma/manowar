#!/bin/bash

set -x

# Run Scheduler Test
./storageAPI.py -d -c ./travis/artifacts/storageAPI.ini > /home/travis/sapi.log &

sapipid=$!

ps "${sapipid}" &> /dev/null

running=$?

if [[ ${running} -eq 0 ]] ; then
	echo "Jellyfish SAPI 2 - UI running with pid ${pid}"
else
	echo "Jellyfish SAPI 2 - UI Not Running. Test Failed"
	exit 1
fi
