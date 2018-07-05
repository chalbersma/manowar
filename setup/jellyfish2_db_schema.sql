create database jellyfish2;

/*
 schema version 1
 Initial Schema Try. Idea is to keep multi-dimensional stuff in an array
 type table "collection." Idea is based upon a talk I heard from
 VividCortex's CEO Baron Schwartz to store time series data as a Vector.
*/

use jellyfish2;

create table hosts (
	host_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
	host_uber_id  INT UNSIGNED,
	hostname VARCHAR(25) NOT NULL,
	pop VARCHAR(10),
	srvtype VARCHAR(25),
	hoststatus VARCHAR(25),
	last_update TIMESTAMP,
	PRIMARY KEY ( host_id ),
	CONSTRAINT host_uber_id UNIQUE (host_uber_id)
);

create or replace index hosts_last_update_index
	on hosts (last_update);

create table collection (
	collection_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
	fk_host_id INT UNSIGNED NOT NULL REFERENCES hosts(host_id),
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

create table audits (
	audit_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
	audit_name VARCHAR(64) NOT NULL,
	/* Priorities should be between 0-10 but it will accept up to 255 */
	audit_priority TINYINT UNSIGNED NOT NULL DEFAULT 5,
	audit_short_description VARCHAR(64) NOT NULL,
	audit_long_description VARCHAR(512),
	/* HTTP Link */
	audit_primary_link VARCHAR(64) NOT NULL,
	/* Secondary Links stored as a BLOB */
	audit_secondary_links BLOB,
	/* Collection Columns */
	audit_filters VARCHAR(512),
	audit_comparison VARCHAR(512),
	filename VARCHAR(512),
	CONSTRAINT audit_name_unique UNIQUE (audit_name),
	PRIMARY KEY (audit_id)
);

create table audits_by_host (
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

create or replace index audits_by_host_vector_index
	on audits_by_host (fk_audits_id, fk_host_id, audit_result, bucket);

create table audits_by_pop (
	pop_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
	pop_text VARCHAR(10) NOT NULL,
	fk_audits_id INT UNSIGNED NOT NULL REFERENCES audits(audit_id),
	pop_initial_audit TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	pop_last_audit TIMESTAMP NOT NULL default '0000-00-00 00:00:00' on UPDATE CURRENT_TIMESTAMP,
	pop_passed BIGINT UNSIGNED NOT NULL,
	pop_failed BIGINT UNSIGNED NOT NULL,
	pop_exempt BIGINT UNSIGNED NOT NULL,
	PRIMARY KEY(pop_id)
);

create or replace index pop_time_index
	on audits_by_pop (fk_audits_id, pop_last_audit);

create table audits_by_srvtype (
	srvtype_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
	srvtype_text VARCHAR(64) NOT NULL,
	fk_audits_id INT UNSIGNED NOT NULL REFERENCES audits(audit_id),
	srvtype_initial_audit TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	srvtype_last_audit TIMESTAMP NOT NULL default '0000-00-00 00:00:00' on UPDATE CURRENT_TIMESTAMP,
	srvtype_passed BIGINT UNSIGNED NOT NULL,
	srvtype_failed BIGINT UNSIGNED NOT NULL,
	srvtype_exempt BIGINT UNSIGNED NOT NULL,
	PRIMARY KEY(srvtype_id)
);

create or replace index srvtype_time_index
	on audits_by_srvtype (fk_audits_id, srvtype_last_audit);

create table audits_by_acoll (
	acoll_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
	acoll_text varchar(64),
	fk_audits_id INT UNSIGNED NOT NULL REFERENCES audits(audit_id),
	acoll_initial_audit TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	acoll_last_audit TIMESTAMP NOT NULL default '0000-00-00 00:00:00' on UPDATE CURRENT_TIMESTAMP,
	acoll_passed BIGINT UNSIGNED NOT NULL,
	acoll_failed BIGINT UNSIGNED NOT NULL,
	acoll_exempt BIGINT UNSIGNED NOT NULL,
	PRIMARY KEY(acoll_id)
);

create or replace index acoll_time_index
	on audits_by_acoll (fk_audits_id, acoll_last_audit);

/* Custom Dashboards */

create table custdashboard (
	custdashboardid INT UNSIGNED NOT NULL AUTO_INCREMENT,
	owner VARCHAR(64) NOT NULL,
	dashboard_name VARCHAR(16),
	dashboard_description MEDIUMTEXT NOT NULL,
	CONSTRAINT dashboard_name UNIQUE(dashboard_name),
	PRIMARY KEY (custdashboardid)
);

create table custdashboardmembers (
	membershipid INT UNSIGNED NOT NULL AUTO_INCREMENT,
	fk_custdashboardid INT UNSIGNED NOT NULL REFERENCES audits(audit_id),
	fk_audits_id INT UNSIGNED NOT NULL REFERENCES audits(audit_id),
	PRIMARY KEY (membershipid),
	CONSTRAINT unique_combo UNIQUE(fk_custdashboardid, fk_audits_id)
);

/* API API
	for robots and sapi
 */

create table apiUsers (
	apiuid INT UNSIGNED NOT NULL AUTO_INCREMENT,
	apiusername VARCHAR(64) NOT NULL,
	apiuser_purpose TEXT,
	CONSTRAINT apiusername UNIQUE (apiusername),
	PRIMARY KEY (apiuid)
);

create or replace index apiusername_index
	on apiUsers (apiusername);
	
create table apiActiveTokens (
	tokenid INT UNSIGNED NOT NULL AUTO_INCREMENT,
	token VARCHAR(512) NOT NULL,
	tokentype VARCHAR(12) NOT NULL,
	fk_apikeyid VARCHAR(64) NOT NULL REFERENCES apiUsers(apikeyid),
	token_issue_date TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	token_expire_date TIMESTAMP NOT NULL default '0000-00-00 00:00:00' on UPDATE CURRENT_TIMESTAMP,
	salt INT UNSIGNED NOT NULL,
	activated BOOL NOT NULL default true,
	PRIMARY KEY (tokenid)
);

create or replace index token_by_userid
	on apiActiveTokens(fk_apikeyid, token);

create table sapiActiveHosts (
	sapihost_record INT UNSIGNED NOT NULL AUTO_INCREMENT,
	fk_host_id INT UNSIGNED NOT NULL REFERENCES hosts(host_id),
	hostname VARCHAR(25) NOT NULL,
	first_seen TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	last_updated TIMESTAMP NOT NULL default '0000-00-00 00:00:00' on UPDATE CURRENT_TIMESTAMP,
	PRIMARY KEY (sapihost_record)
) ; 


/* Archive Tables */

create table collection_archive (
	collection_id BIGINT UNSIGNED NOT NULL,
	fk_host_id INT UNSIGNED NOT NULL,
	initial_update TIMESTAMP NOT NULL,
	last_update TIMESTAMP NOT NULL,
	collection_type VARCHAR(256) NOT NULL,
	collection_subtype VARCHAR(256) NOT NULL,
	collection_value VARCHAR(256),
	PRIMARY KEY (collection_id)
);

create table audits_by_acoll_archive (
	acoll_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
	acoll_text varchar(64),
	fk_audits_id INT UNSIGNED NOT NULL REFERENCES audits(audit_id),
	acoll_initial_audit TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	acoll_last_audit TIMESTAMP NOT NULL default '0000-00-00 00:00:00' on UPDATE CURRENT_TIMESTAMP,
	acoll_passed BIGINT UNSIGNED NOT NULL,
	acoll_failed BIGINT UNSIGNED NOT NULL,
	acoll_exempt BIGINT UNSIGNED NOT NULL,
	PRIMARY KEY(acoll_id)
);

/* IP Intelligence Tables */
create table ip_intel(
	ip_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
	ip_hex VARBINARY(16) NOT NULL,
	fk_host_id INT UNSIGNED NOT NULL REFERENCES hosts(host_id),
	guessed_type ENUM('vips4','vips6','host4','host6','drac4','drac6','netdev4','netdev6','unknown') NOT NULL,
	first_seen TIMESTAMP NOT NULL default CURRENT_TIMESTAMP,
	last_seen TIMESTAMP NOT NULL default CURRENT_TIMESTAMP on UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT ip_hex_unique UNIQUE (ip_hex, fk_host_id, guessed_type),
	PRIMARY KEY (ip_id)
);

create or replace index ip_intel_ip_hex
	on ip_intel (ip_hex);

create or replace index ip_intel_host_to_iphex
	on ip_intel (fk_host_id, ip_hex);

