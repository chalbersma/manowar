"""

"""

from yoyo import step

__depends__ = {'20200107_02_xxxxx-credentials'}

steps = [
    step("alter table hosts add column mresource VARCHAR(64) NOT NULL default hostname",
         "alter table hosts drop column mresource"),
    step("alter table hosts add column mpartition VARCHAR(16) NOT NULL default '' ",
         "alter table hosts drop column mpartition"),
    step("alter table hosts add column mservice VARCHAR(16) NOT NULL default srvtype",
         "alter table hosts drop column mservice"),
    step("alter table hosts add column mregion VARCHAR(16) NOT NULL default pop",
         "alter table hosts drop column mregion"),
    step("alter table hosts add column maccountid VARCHAR(32) NOT NULL default ''",
         "alter table hosts drop column maccountid"),
    step('''alter table hosts add column mownbase VARCHAR(160) NOT NULL 
            default CONCAT('mown://', mpartition, ':', mservice, ':', mregion, ':', maccountid, ':', mresource)
            ''',
         "alter table hosts drop column mownbase"),
    step("alter table hosts add column mownfull VARCHAR(1024) NOT NULL default mownbase",
         "alter table hosts drop column mownfull"),
    step('''alter table hosts add column mowntags TEXT NOT NULL default "{}"''',
         "alter table hosts drop column mowntags"),
    step("alter table hosts add constraint mowntags_is_json CHECK(JSON_VALID(mowntags))",
         "alter table hosts drop constraint mowntags_is_json"),
    step("alter table hosts add constraint mownbase_is_unique UNIQUE(mownbase)",
         "alter table hosts drop constraint mownbase_is_unique"),
]
