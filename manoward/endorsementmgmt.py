#!/usr/bin/env python3

'''
Copyright 2018, VDMS
Licensed under the terms of the BSD 2-clause license. See LICENSE file for terms.
'''

# Validate Endorsements
import logging

from flask import abort


def process_endorsements(endorsements=[], restrictions=[], session_endorsements=[], session_restrictions=[], ignore_abort=False, **kwargs):
    '''
    Process Endorsements

    Looks at the listed restrictions and endorsements for the session and compares them with the endpoint ones. 403 if nedded
    '''

    logger = logging.getLogger("endorsementmgmt.py")

    if ignore_abort is True or kwargs.get("do_abort", True) is False:
        logger.warning("Aborts are off (Likely because of Debug Mode).")

    # Grab All Tokens
    # select * from sapiActiveTokens join sapiUsers on sapiUsers.sapiuid = sapiActiveTokens.fk_sapikeyid where token_expire_date > NOW() ;

    # Grab all the Matching Endorsements
    found_endorsements = [
        endorsement for endorsement in endorsements if endorsement in session_endorsements]

    #logger.debug("Current Session Endorsements : {}".format(found_endorsements))

    # Grab all the Restrictions
    found_restrictions = [
        restriction for restriction in restrictions if restriction in session_restrictions]

    #logger.debug("Current Session Restrictions : {}".format(found_restrictions))

    if len(found_restrictions) > 0:
        # Fail this
        result = (False, found_restrictions)
    elif len(found_endorsements) > 0:
        # Pass this
        result = (True, found_endorsements)
    else:
        # No Endorsments or Restrictions Found
        result = (False, "No Matches")

    if result[0] is False:
        if ignore_abort is False:
            logger.info(
                "Dropping Session {}/{}".format(found_endorsements, found_restrictions))
            logger.debug(
                "Dropping Session with Endorsements/Restrictions {}/{}".format(endorsements, restrictions))
            abort(403)

    return result
