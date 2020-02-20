"""

"""

from yoyo import step

__depends__ = {'20200217_03_MvgoN'}

# Adds a audit uuid for Better Sharding

steps = [
    step('''ALTER TABLE audits
            ADD COLUMN audit_uuid VARCHAR(128) NOT NULL default UUID()''',
         '''ALTER TABLE audits
            DROP COLUMN audit_uuid'''),
    step('''ALTER TABLE audits
            ADD CONSTRAINT unique_audit_uuid UNIQUE(audit_uuid)''',
         '''ALTER TABLE audits
            DROP CONSTRAINT unique_audit_uuid''')

]
