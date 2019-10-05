#!/usr/bin/env python3

'''
This is a Module to provide a common function doing normalish queries
against the MySQL based Backend.
'''

import logging
import pymysql

def func_query(dbcur=False, query=False, query_args=False, **kwargs):

    '''
    Give it a cursor, query and array of arguments (along with some optional
    arguments) and it will run the query, handle common error and return
    a dictionary of the data.
    '''

    logger = logging.getLogger("manowarobj.function_db.func_query")

    query_good = False
    query_results = list()
    purpose = kwargs.get("purpose", "Unspecified Purpose")

    # Allows me to run non/mogrified queries
    cursor_args = [query]

    if query_args is not False:
        cursor_args.append(query_args)

    if dbcur is not False an dquery is not False:

        try:
            debug_query = dbcur.mogrify(*cursor_args)
            logger.debug("{} Debug Query: {}".format(purpose,
                                                     debug_query))
            dbcur.execute(*cursor_args)
        except Exception as database_error:
            logger.error("{} Unable to Run with error : {}".format(purpose,
                                                                   debug_query))
        else:

            query_good = True

            if kwargs.get("oneonly", False) is True:
                # Fetchone
                query_results = dbcur.fetchone()
            else:
                query_results = dbcur.fetchall()

            if kwargs.get("failnone", False) is True and query_results is None:
                logger.error("{} Query Returned no Results on an expected result. Failing.".format(purpose))
                query_good = False

        finally:

            if query_good:
                logger.debug("{} Query Returned {} Results".format(purpose, len(query_results)))
            else:
                logger.warning("{} Query did not Successfully Run.".format(purpose)

    else:
        logger.error("{} Cannot Run query no Query Given.".format(kwargs.get("purpose", "Unspecified Purpose")))

    return query_good, query_results
