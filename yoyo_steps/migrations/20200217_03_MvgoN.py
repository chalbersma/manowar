"""

"""

from yoyo import step

__depends__ = {'20200217_02_lELfo'}

## Lengthen Out Descriptions it's 2020 muthafuckers

steps = [
    step('''ALTER TABLE audits
            MODIFY column audit_long_description LONGTEXT DEFAULT NULL''',
         '''ALTER TABLE audits
            MODIFY column audit_long_description TEXT DEFAULT NULL'''
         ),
    step('''ALTER TABLE audits
            MODIFY column audit_short_description TINYTEXT DEFAULT NULL''',
         '''ALTER TABLE audits
            MODIFY column audit_short_description varchar(64) DEFAULT NULL'''
         ),
    step("create or replace index audit_uuid_index on audits(audit_uuid)",
         "drop index if exists audit_uuid_index on audits")
]
