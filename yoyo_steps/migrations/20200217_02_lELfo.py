"""

"""

from yoyo import step

__depends__ = {'20200217_01_WztFM'}

steps = [
    step('''ALTER table audits
            DROP column audit_secondary_links''',
         '''ALTER table audits
            ADD column audit_secondary_links blob DEFAULT NULL'''),
    step('''ALTER table audits
        DROP column audit_secondary_links2''',
         '''ALTER table audits
            ADD column audit_secondary_links2 TEXT DEFAULT COLUMN_JSON(audit_secondary_links)'''),
    step('''ALTER TABLE audits
        ADD column audit_secondary_links LONGTEXT DEFAULT "{}"''',
         '''ALTER TABLE audits
            DROP column audit_secondary_links'''
         ),
    step('''ALTER TABLE audits
            ADD CONSTRAINT s_links_json CHECK(json_valid(audit_secondary_links))''',
         '''ALTER TABLE audits
            DROP CONSTRAINT s_links_json''')
]
