create user 'manowar_api'@'localhost' identified by 'manowar_api';
grant select, insert, update, delete on manowar.hosts to 'manowar_api'@'localhost';
grant select, insert, update, delete on manowar.collection to 'manowar_api'@'localhost';
grant select, insert, update, delete on manowar.ip_intel to 'manowar_api'@'localhost';
