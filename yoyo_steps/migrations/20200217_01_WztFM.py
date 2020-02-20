"""
Updates to Audit Table to Add New Columns

Also JSONIFYs existing Things
"""
import logging

from yoyo import step

logger = logging.getLogger("yoyo-credentials Step")

# Note this is Destructive on the audit_filters & audit_comparisons Columns
logger.warning("If you have Exising Audits Please run a load --all to reload all your audits.")

__depends__ = {'20200212_01_IcC70'}

steps = [
    step('''ALTER TABLE audits
            MODIFY column audit_long_description TEXT DEFAULT NULL''',
         '''ALTER TABLE audits
            MODIFY column audit_long_description varchar(512) DEFAULT NULL'''
         ),
    step('''ALTER TABLE audits
            MODIFY column audit_filters LONGTEXT DEFAULT '{}' ''',
         '''ALTER TABLE audits
            MODIFY column audit_filters varchar(512) DEFAULT NULL'''
         ),
    step('''ALTER TABLE audits
            MODIFY column audit_comparison LONGTEXT DEFAULT '{}' ''',
         '''ALTER TABLE audits
            MODIFY column audit_comparison varchar(512) DEFAULT NULL'''
         ),
    step('''ALTER TABLE audits
            ADD column audit_version varchar(10) DEFAULT '2.0' ''',
         '''ALTER TABLE audits
            DROP column audit_version'''
         ),
    step('''ALTER TABLE audits
            ADD column audit_ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP''',
         '''ALTER TABLE audits
            DROP column audit_ts'''
         ),
    step('''UPDATE audits set audit_filters = '{}', audit_comparison = '{}'
            where JSON_VALID(audit_filters) = False
                OR JSON_VALID(audit_comparison) = False '''),
    step('''ALTER TABLE audits
            ADD CONSTRAINT filters_json CHECK(json_valid(audit_filters))''',
         '''ALTER TABLE audits
            DROP CONSTRAINT filters_json'''
         ),
    step('''ALTER TABLE audits
            ADD CONSTRAINT comp_json CHECK(json_valid(audit_comparison))''',
         '''ALTER TABLE audits
            DROP CONSTRAINT comp_json'''
         ),
    # TWO Step here to Convert asl to JSON Text
    step('''ALTER TABLE audits
            ADD column audit_secondary_links2 TEXT DEFAULT COLUMN_JSON(audit_secondary_links)''',
         '''ALTER TABLE audits
            DROP column audit_secondary_links2'''
         )

]
