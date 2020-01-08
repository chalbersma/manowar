#!/bin/bash

set -x

# Run Scheduler Test
./ui.py -d -c ./travis/artifacts/ui.yaml > /home/travis/ui.log &

uipid=$!

ps "${uipid}" &> /dev/null

running=$?

if [[ ${running} -eq 0 ]] ; then
	echo "Jellyfish 2 - UI running with pid ${uipid}"
else
	echo "Jellyfish 2 - UI Not Running. Test Failed"
	exit 1
fi
