# Analyze

## Introduction

The analyze module runs independently. It will, using the audits as defined in
`audits.d` directory, analyze the collections table to find out which hosts passed
or failed the audits. Then it stores the results in the `audits_by_host` table.
It assigns a unique audit result id, the id numbers for the host and audit, the
timestamps associated with this result, which bucket this result is in the result
& optionally the result text.

These audit results power the dashboard that is used by jellyfish and are the
expected way to interact and process data within the Jellyfish system.

## Audits

Audits are stored in the
[jellyfishaudits](pages)
project. There you'll find some documentation on the content and structure of
documentation that's available to you.

## Analyze Architecture

![Analyze Code Architecture](/plantuml/analyze_diagram.svg)

The general idea of analyze is quite simple. The process :

1. Grabs a lists of hosts
1. Uses `generic_large_compare` to find out which hosts are in which bucket
1. For Each Bucket:
    * Uses either `generic_large_compare` or `subtype_large_compare` to compute
      passing or failing scores.
    * Uses `generic_large_analysis_store` to store results in `audits_by_host`
      table in the database.

## Generic Large Analysis Store

This module is a big part of the reason that autocommits were turned off. By batching
up all the inserts/updates together we avoid an row locking race condition on the
database.

## Future State

This is a candidate for creating a lambda esque method of generating this data.
Because of the nature of lambda you could simplify this code to check one host
against one audit where every check will see which (or if) bucket it falls into
and then flood your DB using lambda execution limits to make sure you dont' hammer
your database.
