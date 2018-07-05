# Collection Archive

The collections table is big and while it is (in my opinion) well indexed even well
indexed tables get too big eventually. This implments archiving of older collection
data. Data that has been obsolete for 7 days get's moved from the `collection` table
to the `collection_archive` table.

This get's ran daily as a part of the `run_schedule.sh` job sequence.

## Future

It's likely that this could be made obsolete in the future with better sharding.
Additionally this could probably be turned into a serverless function if ever the
decision was made to migrate to the cloud.
