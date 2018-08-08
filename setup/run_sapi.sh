#!/bin/bash

# Copyright 2018, VDMS
# Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

# Startup Script for Jellyfish 2 - SAPI

# Until We Go Prod Use the Test CSV
PIDFile=jfish2-sapi.pid
SAPIConfig=storageAPI.ini
J2RunLoc=secops
SAPILog=storageAPI.log

if [[ -w ${PIDFile} ]] ; then
	pid=$(cat ${PIDFile})
	kill -0 "${pid}"
	foundpid=$?
	if [[ ${foundpid} -eq 0 ]] ; then
		echo -e "Jellyfish 2 - SAPI Currently Running with pid: ${pid}. Exiting"
		exit 1
	else
		# Process Exists
		rm -f ${PIDFile}
	fi
elif [[ -e ${PIDFile} ]] ; then
	# Pid file exists but I can't write to it. Don't try to start
	echo -e "Pid File ${PIDFile} cannot be written to. Are you root?"
	exit 1
fi

# Okay we either cleanedup our stale pid file or no stale pid file exists
# Rotate Sched Log
last_loc=${SAPILog}.9

# Rotate Logs
for i in {8..1} ; do
	# Copy Log # to Log -1 (First one goes to /dev/null)
	cp  ${SAPILog}.${i} ${last_loc}
	# Change this log location to ${last_loc}
	last_loc="${SAPILog}.${i}"
done

# Copy the latest to the latest
cp ${SAPILog} ${SAPILog}.1

# Activate Virtual Env
# shellcheck disable=SC1090
source ${J2RunLoc}/bin/activate

# Run the Scheduler And fork to background
${J2RunLoc}/storageAPI.py -c ${SAPIConfig}  &> ${SAPILog} &

# Grab that Pid
J2Pid=$!

# Toss that PID to my PID File
echo "${J2Pid}" > "${PIDFile}"

# Fuck outta here
exit 0

