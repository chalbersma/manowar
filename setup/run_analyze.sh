#!/bin/bash

# Copyright 2018, VDMS
# Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.

# Variables
# Until We Go Prod Use the Test CSV
#CSVFile=/oc/local/netinfo/etc/servers4.csv
#CSVFile=/oc/local/netinfo/etc/servers4_example.csv

# Set these Variables
AnalyzeConfig=analyze.ini
CollateConfig=collate.ini
AuditdLoc=audits.d
BassAuditLoc=bass
J2RunLoc=jellyfish
SchedLog=/var/log/analyze.log
AnalyzeLockFile=/var/run/jfish2-analyze.lock
SchedLockFile=/var/run/jfish2-scheduler.lock

if [[ -e ${SchedLockFile} ]] ; then
	echo -e "At $(date +%s) A new instance of analyze tried to run but stopped because of an existing lockfile at ${SchedLockFile}. Indicating that a Collection is Running." >> ${SchedLog}
	exit 0
	# Add Future Alerting Here
elif [[ -e ${AnalyzeLockFile} ]] ; then
	echo -e "At $(date +%s) A new instance of analyze tried to run but stopped because of an existing lockfile at ${AnalyzeLockFile}." >> ${SchedLog}
	exit 0
	# Add Future Alerting Here.
else
	touch ${AnalyzeLockFile}
	# Trap exit
    # shellcheck disable=SC2154
	trap 'rc=$?; rm -f  ${AnalyzeLockFile}; exit ${rc}' EXIT
fi




# Rotate Sched Log
last_loc=${SchedLog}.9
for i in {8..1} ; do
	# Copy Log # to Log -1 (First one goes to /dev/null)
	cp  ${SchedLog}.${i} ${last_loc}
	# Change this log location to ${last_loc}
	last_loc="${SchedLog}.${i}"
done

# Copy the latest to the latest
cp ${SchedLog} ${SchedLog}.1

# Activate Virtual Env
# shellcheck disable=SC1090
source ${J2RunLoc}/bin/activate

# Run the Scheduler
# Use Analyze Mode so Verbosity On
#${J2RunLoc}/analyze.py -c ${AnalyzeConfig} -a ${AuditdLoc} &> ${SchedLog}
${J2RunLoc}/analyze.py -c ${AnalyzeConfig} -a ${AuditdLoc} -a ${BassAuditLoc} -V &> ${SchedLog}

echo "Starting Collation" >> ${SchedLog}

#${J2RunLoc}/collate.py -c ${CollateConfig} &>> ${SchedLog}
${J2RunLoc}/collate.py -c ${CollateConfig} -V &>> ${SchedLog}

## Clear Cache

find /var/run/manowar/cache/ -print0 | xargs -0 rm

