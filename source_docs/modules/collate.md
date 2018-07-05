# Collate

## Introduction

We used to collate in-line in the Analyze module. However that proved to be quite
costly. So we moved to a system where we analyze and then we collate our data seperately.
This module does that. It figures passed, failed and exempt audits on a per-audit,
per-pop and per-srvtype basis.

## Arch

![Collate Architecture](/plantuml/collate_diagram.svg)

The idea here is simple. It will cycle through the various by factors (pop, srvtype
audit/acoll). It counts up the results in `audits_by_host` for each of these
factors and then update the related numbers in `audits_by_factor`.

## Future State

This probably couldn't be moved to a lambda (unless the future database is quite
quick) but it could be an excellent candidate for [Amazon Glue](https://aws.amazon.com/glue/)
as it's in effect a simplistic ETL job.

