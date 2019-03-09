#!/bin/bash

set -x

## Setup DB Schema

sudo mysql -u root -e "show full processlist;"

sudo bash -c "mysql -u root < setup/manowar_db_schema.sql"

schema_success=$?

if [[ "${schema_success}" -eq 0 ]] ; then
	echo "DB Schema Successfully setup. ${schema_success}"
else
	echo "DB Schema has an issue, please investigate. ${schema_success}"
	exit 1
fi
