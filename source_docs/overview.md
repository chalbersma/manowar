# Man o' War

## Introduction

Man o' War has a goal of collecting more data, allowing historical lookbacks, and
providing a more flexible auditing solution. Additionally it has a goal of having
a flexible model for metadata storage so that future collection and analysis needs
can be met.

## Man o' War Overview

Man o' War is a follows the Unix philosophy of designing small modules to do a job
well and then tie those modules together to do more complex things. At the moment
Jellyfish is composed of 12 modules (with more being added as needed):

* Analyze
* BundleUSNs
* Collate
* Collector
* PullSwagger
* Schedule
* ScrapeUSN
* StorageAPI
* StorageJSONVerify
* Storage
* UI
* VerifyAudits

Each module has a specific purpose and is deisgned to be able to run independently
from each other (for ease of troubleshooting). They're brought together by either
calling each other or by helper scripts (to be called by cron or init). There are
several ideas for which module should come next. We always love pull requests so
feel free to let us know about a few.

## Modules

### Collector

The collector is designed to grab data back for one host. The first and current
collector utilizes paramiko/ssh to log onto it's host, run a series of commands
configured in `collector.ini` (and stored in SVN). If ran by hand you can utilize
command line flags to test the data being given by a particular host. The collector
will return a json or python dictionary that meets the standards specified in
`travis/artifacts/jellyfish_storage.json.schema`. You can utilize the
StorageJSONVerify module to confirm the goodness (or badness) of a particular set
of data.

### Storage

The storage module is designed to take json from a collector (that meets the
`travis/artifacts/jellyfish_storage.json.schema` specification) and "do the right thing" for storage.
For each collection it will query the database to see if there are changes. If there
are, it will insert a new record with the proper timestamps. If there are not, it
will update the existing record with the the current time (more specifically the
time noted in the json); unless the time given is less than the time currently on
disk (think of race conditions). Data is stored in the database as "Vectors" with
the time being the magnitude of the vector & the various data as the direction (See
Diagram).

The Database the storage module uses is a MariaDB 10.1 (or higher) database. It's connection
details are configured in `storage.ini`. Additionally it's schema is stored in the
`setup/jellyfish2_db_schema.sql`.

### Scheduler

The scheduler is called by cron (at the moment) and it is fenced with a lockfile
in `/var/run/jellyfish` (should be somewhat configurable). The scheduler utilizes a configurable amount of threads
(configured in `travis/artifacts/scheduler.ini` as an example) to run a number of instances of the Collector
& Storage modules. It uses the `server4.csv` file located in the netinfo svn
location to grab a list of servers it needs to check.

The module will quit after a certain amount of time where it can't reach all the
hosts. In this scenario it will return an item in the output json that looks like
this:

		"Timeout": "Timeout reached at 57627.98305392265 seconds with 29 items left on the queue.",

The Verbose module will output a status message to stdout for the duration of the
run. Additionally a final status json will be outputted to stdout (and optionally
to a seperate file) that contains the following pieces of information:

* `global_fail_hosts` - How many hosts scheduler failed to collect data from
* `global_fail_hosts_list` - A list of those hosts
* `global_fail_prod` - How many hosts scheduler failed to collect data from that
	were listed as "production" in their uber status.
* `global_fail_prod_list` - A list of those production hosts.
* `global_success_hosts` - How many hosts scheduler successfully collected data from.
* `global_success_hosts_list` - A list of those hosts.
* `jobtime` - How long, in seconds, scheduler ran for.
* `threads` - How many threads the system used

### Analyze

See [modules/analyze](modules/analyze.md).

### Collate

See [modules/collate](modules/collate.md).

### Verify Audits

Verify audits will verify either a single audit or a recursive dictionary of audits
to see if they "make sense." This module makes heavy use of the `ast.literal_eval`
to parse and analyze a file. It's utilized by several modules to verify that an
audit makes sense before it is analyzed.

### Pull Swagger

PullSwagger is a little tool that will recurse through a direcotry of python files
and pull the first fenced swagger definition out of that file. Then it utilizes
a jinja template (currenltly located at `openapi3/openapi3.yml.jinja` in SVN)
to build a Swagger definition file from it. Currently it's used for the
`jelly_api_2` directory to pull a file that get's displayed here.

### Storage JSON Verify

Is a module that will check a particular JSON file against json schema file
(`travis/jellyfish_storage.json.schema` in SVN) to see if it's valid. In theory it can
check any given json against any given json schema file.

### UI

It's a flask app that can be controlled on the main box by a service command
(jellyfish2-ui). Additionally there's an Apache forwarder configured to point
back to this flask app and provide LDAP authentication.
