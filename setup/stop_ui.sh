#!/bin/bash

# Copyright 2018, VDMS
# Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

# Stop Script for Jellyfish 2 - UI

# Exit 2 Means try it again

# Until We Go Prod Use the Test CSV
#CSVFile=servers4.csv
#CSVFile=servers4_example.csv
PIDFile=jfish2-ui.pid
#J2RunLoc=secops
#UILog=ui.log

if [[ -w ${PIDFile} ]] ; then
	pid=$(cat ${PIDFile})
	ps "${pid}" &> /dev/null
	if [[ $? -eq 0 ]] ; then
		# PID Exists Kill it
		kill "${pid}"
		# Check if it worked (Ignore errors for no)
		ps "${pid}" &> /dev/null
		still_running=$?
		if [[ ${still_running} -ne 0 ]]; then
			# Pid found (still running)
			echo -e "Jellyfish 2 - UI Could Not Kill Process ${pid}."
			exit 2
		else
			# Pid not found (stopped Running)
			# Kill my PID FIle
			rm -f ${PIDFile}
			# Echo and Leave
			echo -e "Jellyfish 2 - UI Stopped."
			exit 0
		fi
	else
		rm -f ${PIDFile}
		if [[ -e ${PIDFile} ]] ; then
			echo -e "Jellyfish 2 - UI Stopped Previously. Could Not Cleanup Pid File."
			exit 1
		else
			echo -e "Jellyfish 2 - UI Stopped Previously. Cleaned up Pid File."
			exit 0
		fi
	fi
elif [[ -e ${PIDFile} ]] ; then
	# Pid file exists but I can't write to it. Don't try to start
	echo -e "Pid File ${PIDFile} cannot be written to. Are you root?"
	exit 1
else
	echo -e "Jellyfish 2 - UI. No Process to stop."
	exit 0
fi
