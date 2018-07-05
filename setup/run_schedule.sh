#!/bin/bash

# Copyright 2018, VDMS
# Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

# Variables
# Until We Go Prod Use the Test CSV
CSVFile=servers4.csv
#CSVFile=servers4_example.csv
SCHEDConfig=scheduler.ini
J2RunLoc=secops
SchedLog=schedlog.log
SchedLockFile=jfish2-scheduler.lock
StoreConfig=storage.ini
TunSocket=jfish_ctrl_socket

RUN_LOC=/tmp
# Exit if it fails
cd ${RUN_LOC} || exit 1

# Check Lock File
if [[ -e ${SchedLockFile} ]] ; then
	echo -e "At $(date +%s) A new instance of analyze tried to run but stopped because of an existing lockfile at ${SchedLockFile}." >> ${SchedLog}
	exit 0
	# Add Future Alerting Here.
else
	touch ${SchedLockFile}
	# Trap exit
    # shellcheck disable=SC2154
	trap 'rc=$?; rm -f  ${SchedLockFile}; exit ${rc}' EXIT
fi


# Rotate Sched Log
last_loc=${SchedLog}.9
for i in {8..1} ; do
	# Copy Log # to Log -1 (First one goes to /dev/null)
	cp  ${SchedLog}.${i} ${last_loc}
	# Change this log location to ${last_loc}
	last_loc="${SchedLog}.${i}"
done

# Check if Tunnelling Desired
# Disabling Tunnelling EC Specific Thing


# Copy the latest to the latest
cp ${SchedLog} ${SchedLog}.1

# Activate Virtual Env
# shellcheck disable=SC1090
source ${J2RunLoc}/bin/activate

# Run the Scheduler 
# Still in Pre-Release so Use Verbose Mode
${J2RunLoc}/schedule2.py -b ${CSVFile} -c ${SCHEDConfig} -V &> ${SchedLog}
#${J2RunLoc}/schedule.py -b ${CSVFile} -c ${SCHEDConfig} &> ${SchedLog}

# Run The Archive Script
${J2RunLoc}/collection_archive.py -c ${StoreConfig} -V &>> ${SchedLog}

if [[ ${use_tun} == true ]] ; then
	# We're using a tunnel so Kill it
	ssh -S ${TunSocket} -O exit jellyfish@deputy001.bur
fi
