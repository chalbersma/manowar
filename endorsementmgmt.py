#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# Validate Endorsements

from flask import abort

def process_endorsements(endorsements=[], restrictions=[], session_endorsements=[], session_restrictions=[], do_abort=False) :

    # Grab All Tokens
    # select * from sapiActiveTokens join sapiUsers on sapiUsers.sapiuid = sapiActiveTokens.fk_sapikeyid where token_expire_date > NOW() ;

    # Grab all the Matching Endorsements
    found_endorsements = [ endorsement for endorsement in endorsements if endorsement in session_endorsements ]

    # Grab all the Restrictions
    found_restrictions = [ restriction for restriction in restrictions if restriction in session_restrictions ]

    if len(found_restrictions) > 0 :
        # Fail this
        result = ( False, found_restrictions )
    elif len(found_endorsements) > 0 :
        # Pass this
        result = ( True, found_endorsements )
    else :
        # No Endorsments or Restrictions Found
        result = ( False, "No Matches" )

    if result[0] == False :
        if do_abort == True :
            abort(403)

    return result
