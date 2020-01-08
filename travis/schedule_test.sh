#!/bin/bash

set -x

# Run Scheduler Test
./schedule2.py -c travis/artifacts/scheduler.ini -b travis/artifacts/servers4.csv -V

# Now Test it WOrks
whereis jq

success_threads=$(jq '.global_success_hosts' < /home/travis/sched_output.json )
fail_threads=$(jq '.global_fail_hosts' < /home/travis/sched_output.json )

if [[ ${success_threads:-0} -eq 0 ]] ; then
	# Failure!
	echo -e "Zero Successful Collections. Total Collections: ${success_threads}"
	exit 1
elif [[ ${fail_threads:-0} -gt 0 ]] ; then
	# Failure!
	echo -e "Fail Threads Collections. Total Collections: ${fail_threads}"
	exit 1
else
	echo -e "Schedule Test appears Successful."
fi

hostcollection_test="$(mktemp /tmp/hctest.XXXXX)"
# Test that it landed properly. Grab the results for host #1
sudo bash -c "mysql manowar2 -u root < travis/artifacts/test_hostcollection.sql > ${hostcollection_test} "

didit=$?

if [[ ${didit:-0} -eq 0 ]] ; then
	# If Worked
	results_found=$(wc -l < "${hostcollection_test}")
	if [[ ${results_found:-0} -gt 0 ]] ; then
		# There are results
		echo -e "Testing host 1, found ${results_found} collections. Appears good."
		echo -e "Debug info for host. Printing Collections."
		#cat "${hostcollection_test}"
	else
		# Didn't Find any results
		echo -e "Testing host 1, found no collections. This is an error."
		exit 1
	fi
else
	echo -e "test_hostcollection.sql didn't work properly. Please investigate travis configuration."
	exit 1
fi

ip_intel_test="$(mktemp /tmp/ipintel.XXXXX)"

# Test that it landed properly. Grab the results for host #1
sudo bash -c "mysql manowar2 -u root < travis/artifacts/test_ipintel.sql > ${ip_intel_test} "

didit_ipintel=$?

if [[ ${didit_ipintel:-0} -eq 0 ]] ; then
	# If Worked
	results_found=$(wc -l < "${ip_intel_test}")
	if [[ ${results_found:-0} -gt 0 ]] ; then
		# There are results
		echo -e "Testing host 1, found ${results_found} Intel Entries. Looks Good"
		echo -e "Debug info for host. Printing IP Intel"
		cat "${ip_intel_test}"
	else
		# Didn't Find any results
		echo -e "Testing host 1, found no intel. This is an error."
		exit 1
	fi
else
	echo -e "test_ipintel.sql didn't work properly. Please investigate travis configuration."
	exit 1
fi
