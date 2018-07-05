#!/bin/bash

# Copyright 2018, VDMS
# Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

# Startup Script for Jellyfish 2 - UI

# Until We Go Prod Use the Test CSV
#CSVFile=servers4.csv
#CSVFile=servers4_example.csv
PIDFile=jfish2-sapi.pid

if [[ -e ${PIDFile} ]] ; then
	pid=$(cat ${PIDFile})
	kill -0 "${pid}"
	running=$?
	if [[ ${running} -eq 0 ]] ; then
		echo "Jellyfish 2 - SAPI running with pid ${pid}"
		exit 0
	else
		echo "Jellyfish 2 - SAPI Not Running. Cleanup Needed."
		exit 1
	fi
else
	echo "Jellyfish 2 - SAPI Not Running."
	exit 1
fi
