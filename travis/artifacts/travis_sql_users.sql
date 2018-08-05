/* Hey Dummy! Don't use these passwords in Production. These are for Travis testing only. */

/* jellyfish_store User */
create user 'jellyfish_store'@'localhost' identified by 'travis_store';
grant insert, update, select, delete on jellyfish2.hosts to 'jellyfish_store'@'localhost';
grant insert, update, select, delete on jellyfish2.collection to 'jellyfish_store'@'localhost';
grant insert, update, select, delete on jellyfish2.collection_archive to 'jellyfish_store'@'localhost';
grant insert, update, select, delete on jellyfish2.audits_by_acoll_archive to 'jellyfish_store'@'localhost';
grant insert, update, select, delete on jellyfish2.sapiActiveHosts to 'jellyfish_store'@'localhost';

show grants for  'jellyfish_store'@'localhost';

/* jellyfish_storeapi User */
create user 'jellyfish_storeapi'@'localhost' identified by 'travis_storeapi';
grant insert, update, select, delete on jellyfish2.hosts to 'jellyfish_storeapi'@'localhost';
grant insert, update, select, delete on jellyfish2.collection to 'jellyfish_storeapi'@'localhost';
grant insert, update, select, delete on jellyfish2.sapiActiveHosts to 'jellyfish_storeapi'@'localhost';
grant insert, update, select, delete on jellyfish2.ip_intel to 'jellyfish_storeapi'@'localhost';
grant select on jellyfish2.apiUsers to 'jellyfish_storeapi'@'localhost';
grant select on jellyfish2.apiActiveTokens to 'jellyfish_storeapi'@'localhost';
show grants for  'jellyfish_storeapi'@'localhost';

/* jellyfish_analyze User */
create user 'jellyfish_analyze'@'localhost' identified by 'travis_analyze';
grant insert, update, select, delete on jellyfish2.audits to 'jellyfish_analyze'@'localhost';
grant insert, update, select, delete on jellyfish2.audits_by_host to 'jellyfish_analyze'@'localhost';
grant insert, update, select, delete on jellyfish2.audits_by_pop to 'jellyfish_analyze'@'localhost';
grant insert, update, select, delete on jellyfish2.audits_by_srvtype to 'jellyfish_analyze'@'localhost';
grant insert, update, select, delete on jellyfish2.audits_by_acoll to 'jellyfish_analyze'@'localhost';
grant select on jellyfish2.hosts to 'jellyfish_analyze'@'localhost';
grant select on jellyfish2.collection to 'jellyfish_analyze'@'localhost';
show grants for  'jellyfish_analyze'@'localhost';

/* jellyfish_ui User */
create user 'jellyfish_ui'@'localhost' identified by 'travis_ui';
grant select on jellyfish2.* to 'jellyfish_ui'@'localhost';
/* For Token Mangaement */
grant insert, update, delete on jellyfish2.apiUsers to 'jellyfish_ui'@'localhost';
grant insert, update, delete on jellyfish2.apiActiveTokens to 'jellyfish_ui'@'localhost';
grant insert, update, delete on jellyfish2.custdashboard to 'jellyfish_ui'@'localhost';
grant insert, update, delete on jellyfish2.custdashboardmembers to 'jellyfish_ui'@'localhost';
/* For migration of storage api endpoints to the main ui interface */
grant insert, update, select, delete on jellyfish2.hosts to 'jellyfish_ui'@'localhost';
grant insert, update, select, delete on jellyfish2.collection to 'jellyfish_ui'@'localhost';
grant insert, update, select, delete on jellyfish2.sapiActiveHosts to 'jellyfish_ui'@'localhost';
grant insert, update, select, delete on jellyfish2.ip_intel to 'jellyfish_ui'@'localhost';
show grants for 'jellyfish_ui'@'localhost';

/* jellyfish_gap User*/
create user 'jellyfish_gap'@'localhost' identified by 'travis_gap';
grant select on jellyfish2.hosts to 'jellyfish_gap'@'localhost';

