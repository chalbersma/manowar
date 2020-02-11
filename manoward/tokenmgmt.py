#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

import hashlib

# Validate Key


def validate_key(username=None, giventoken=None, dbcur=None, tokentype="sapi"):

    # Grab All Tokens
    # select * from sapiActiveTokens join sapiUsers on sapiUsers.sapiuid = sapiActiveTokens.fk_sapikeyid where token_expire_date > NOW() ;

    if username == None:
        return False
    elif giventoken == None:
        return False
    elif dbcur == None:
        return False

    available_tokens_sql = '''select apiUsers.apiuid
                                from apiActiveTokens
                                join apiUsers on apiUsers.apiuid = apiActiveTokens.fk_apikeyid
                                where token_expire_date > NOW()
                                and apiUsers.apiusername = %s
                                and tokentype = %s
                                and token=SHA2(CONCAT(salt,%s),512)'''

    token_sql_values = (username, tokentype, giventoken)

    # Get My User's Tokens

    try:
        #print(dbcur.mogrify(available_tokens_sql, token_sql_values))
        dbcur.execute(available_tokens_sql, token_sql_values)
        all_tokens = dbcur.fetchone()
    except Exception as error:
        print("Error with DB Connection, ", str(error))
        return False
    else:
        if all_tokens == None:
            # No Tokens Found
            return False
        else:
            # There was a match!
            return True
    return False
