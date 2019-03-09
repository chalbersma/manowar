CREATE DATABASE manowar CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

/*
 schema version 1
 Initial Schema Try. Idea is to keep multi-dimensional stuff in an array
 type table "collection." Idea is based upon a talk I heard from
 VividCortex's CEO Baron Schwartz to store time series data as a Vector.
*/

use manowar;

/* Changes
- BIGINT for ids
- endorsees as a JSON array of configurable endorsements. Gives user level RBAC
*/

create table hosts (
	host_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
	external_id VARCHAR(64),
	hostname VARCHAR(25) NOT NULL,
	pop VARCHAR(10),
	srvtype VARCHAR(25),
	hoststatus VARCHAR(25),
	last_update TIMESTAMP,
	endorsees TINYTEXT DEFAULT "[\"default\"]",
	tags TINYTEXT DEFAULT "{\"default\":true}",
	PRIMARY KEY (host_id),
	CONSTRAINT endorsees_json CHECK(JSON_VALID(endorsees)),
	CONSTRAINT tags CHECK(JSON_VALID(tags)),
	CONSTRAINT ext_id_unique UNIQUE (external_id),
	CONSTRAINT hostname_unique UNIQUE (hostname)
);

create or replace index hosts_last_update_index
	on hosts (last_update);

create or replace index hosts_by_hostname
	on hosts (hostname);

create or replace index hosts_by_extid
	on hosts (external_id);


/*
This may still end up being a bad idea.
*/

create table collection (
	collection_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
	fk_host_id BIGINT NOT NULL REFERENCES hosts(host_id),
	initial_update TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	last_update TIMESTAMP NOT NULL default '0000-00-00 00:00:00' on UPDATE CURRENT_TIMESTAMP,
	collection_type VARCHAR(256) NOT NULL,
	collection_subtype VARCHAR(256) NOT NULL,
	collection_value VARCHAR(256),
	PRIMARY KEY (collection_id)
);

create or replace index fk_host_id
  on collection (fk_host_id) ;

create or replace index generic_collection_index
	on collection (fk_host_id, collection_type, collection_subtype, last_update);

create or replace index type_subtype_index
	on collection (collection_type, collection_subtype);

create or replace index collection_type_index
	on collection (last_update, collection_type, collection_subtype );

create or replace index host_index
        on collection (fk_host_id);

/*
Instead of relying on the audit nodes having a full copy of the audit description,
Instead I'm going to store a JSONic representation of the audit in the database
that they can query and use.

Now I can break audits out to multiple systems provided that they all have direct
or network database access.
*/

create table audits (
	audit_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
	audit_name VARCHAR(64) NOT NULL,
	/* Priorities should be between 0-10 but it will accept up to 255 */
	audit_priority TINYINT UNSIGNED NOT NULL DEFAULT 5,
	audit_obj LONGTEXT,
	validates BOOL default True,
	CONSTRAINT audit_name_unique UNIQUE (audit_name),
	CONSTRAINT audit_obj_valid_json CHECK(JSON_VALID(audit_obj)),
	PRIMARY KEY (audit_id)
);

/*
Going to get rid of audit_result_by blah tables focus on delivering one
audit_results tables. Let audit results be index by the endorsees in the
hosts table.
*/

create table audit_results (
	audit_result_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
	fk_host_id INT UNSIGNED NOT NULL REFERENCES hosts(host_id),
	fk_audits_id INT UNSIGNED NOT NULL REFERENCES audits(audit_id),
	initial_audit TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	last_audit TIMESTAMP NOT NULL default '0000-00-00 00:00:00' on UPDATE CURRENT_TIMESTAMP,
	bucket VARCHAR(64),
	audit_result ENUM('pass','fail','notafflicted'),
	audit_result_text VARCHAR(256),
	PRIMARY KEY (audit_result_id)
);

/*
Fun times here. Going to demand a users table, i know might not be the best
idea but I'm thinking i can rely on forwarded credentials and a rules
engine to find out what endorsements a user should have.
*/

create table users (
	userid INT UNSIGNED NOT NULL AUTO_INCREMENT,
	username VARCHAR(64) NOT NULL,
	user_purpose TEXT,
	is_human BOOL NOT NULL DEFAULT TRUE,
	endorsements TINYTEXT DEFAULT "[\"default\"]",
	CONSTRAINT username_unique UNIQUE (userid),
	PRIMARY KEY (userid)
);

create or replace index username_index
	on users (username);

create table tokens (
	tokenid INT UNSIGNED NOT NULL AUTO_INCREMENT,
	token VARCHAR(512) NOT NULL,
	fk_userid VARCHAR(64) NOT NULL REFERENCES users(userid),
	token_issue_date TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	token_expire_date TIMESTAMP NOT NULL default '0000-00-00 00:00:00' on UPDATE CURRENT_TIMESTAMP,
	salt INT UNSIGNED NOT NULL,
	activated BOOL NOT NULL default true,
	PRIMARY KEY (tokenid)
);

create or replace index token_by_userid
	on tokens(fk_userid, token);

/* IP Intelligence Tables
Geting rid of edgecastic definitions of IPS and going more general. ip_hex should be large enough to store any IPV6 ip address.
*/

create table ip_intel(
	ip_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
	ip_hex VARBINARY(16) NOT NULL,
	fk_host_id INT UNSIGNED NOT NULL REFERENCES hosts(host_id),
	guessed_type ENUM('nonexclusive','exclusive','unknown') NOT NULL,
	first_seen TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	last_seen TIMESTAMP NOT NULL default CURRENT_TIMESTAMP on UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT ip_hex_unique UNIQUE (ip_hex, fk_host_id, guessed_type),
	PRIMARY KEY (ip_id)
);

create or replace index ip_intel_ip_hex
	on ip_intel (ip_hex);

create or replace index ip_intel_host_to_iphex
	on ip_intel (fk_host_id, ip_hex);
