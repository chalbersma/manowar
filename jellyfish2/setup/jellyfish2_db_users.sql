/* jellyfish_store User */
create user 'jellyfish_store'@'localhost' identified by 'OWSV7o9RDMomCRbJJt1gHobFvC8h5o0i';
grant insert, update, select, delete on jellyfish2.hosts to 'jellyfish_store'@'localhost';
grant insert, update, select, delete on jellyfish2.collection to 'jellyfish_store'@'localhost';
show grants for  'jellyfish_store'@'localhost';

/* jellyfish_storeapi User */
create user 'jellyfish_storeapi'@'localhost' identified by 'kRa4pW58Qd3Tg0nXGwbggy1P8Mxcf5H4';
grant insert, update, select, delete on jellyfish2.hosts to 'jellyfish_storeapi'@'localhost';
grant insert, update, select, delete on jellyfish2.collection to 'jellyfish_storeapi'@'localhost';
show grants for  'jellyfish_storeapi'@'localhost';

/* jellyfish_analyze User */
create user 'jellyfish_analyze'@'localhost' identified by 'rATmCKHETK6RurUuAhgZ3sgQhDlCv8sA';
grant insert, update, select, delete on jellyfish2.audits to 'jellyfish_analyze'@'localhost';
grant insert, update, select, delete on jellyfish2.audits_by_host to 'jellyfish_analyze'@'localhost';
grant insert, update, select, delete on jellyfish2.audits_by_pop to 'jellyfish_analyze'@'localhost';
grant insert, update, select, delete on jellyfish2.audits_by_srvtype to 'jellyfish_analyze'@'localhost';
grant insert, update, select, delete on jellyfish2.audits_by_acoll to 'jellyfish_analyze'@'localhost';
grant select on jellyfish2.hosts to 'jellyfish_analyze'@'localhost';
grant select on jellyfish2.collection to 'jellyfish_analyze'@'localhost';
show grants for  'jellyfish_analyze'@'localhost';

/* jellyfish_ui User */
create user 'jellyfish_ui'@'localhost' identified by 'rcDfNEcSxTQ6Gbr6zg8TQO41udg3eQPZ';
grant select on jellyfish2.* to 'jellyfish_ui'@'localhost';
show grants for 'jellyfish_ui'@'localhost';
