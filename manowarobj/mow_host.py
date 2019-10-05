#!/usr/bin/env python3

'''
mow_host.py contains the definition for mowHost (manowar Host)
which grabs data back about hosts.
'''

import pymysql
import logging
import datetime

from manowarobj.function_db import func_query

import saltcell.mown

class MOWHost():

    __json_columns = ["mresource_meta", "endorsees", "tags"]

    __init__(**kwargs):

        self.logger = logging.getLogger("manowarobj.mow_host.MOWHost")

        self.kwargs = kwargs
        self.endorsements = self.kwargs.get("endorsements", ["default"])

        if self.kwagrs.get("dbcur", False) is False and (self.kwargs.get("mown_base", False) is False and
                                                         self.kwargs.get("asset_uuid", False) is False):
            # I don't have a cursor or a hostid to use to grab my latest.
            # This must be a new entry
            if self.kwargs.get("collection_object", False) is False:
                pass
            else:
                self.logger.warning("Object doesn't have enough data to know what I'm doing.")
        elif:
            # I have the data I need to Pull Back the curtain Go Get and Populate My Host Data
            loaded, self.mown_data = self.load_from_db()

    def load_given_data(self, collection_object=False):

        '''
        Take the Object You've gotten from the API endpoint and then store it in the database.
        '''

        if collection_object is False:
            self.logger.error("Cannot load from given data with no given data.")
            raise ValueError("no collection object give")

        if "mown_full" not in collection_object.keys():
            self.logger.error("mwon_full not specified in given data.")
            raise ValueError("Missing MOWN Full on New/Updated Data")

        given_mown = saltcell.mown(uri=collection_object["mown_full"])

        found_existing, existing = self.load_from_db

    def load_from_db(self, mown_base=False, asset_uuid=False):

        '''
        Load This Object from my Database

        If it's there load it. And parse the JSON bits
        '''

        loaded_good = False
        result = dict()

        if self.kwargs.get("mown_base", False) is not False or mown_base is not False:
            get_query = "select * from assets where mwon_base = %s order by last_update desc limit 1"
            get_args = self.kwargs.get("mown_base")
        elif self.kwargs.get("asset_uuid", False) is not False or asset_uuid is not False:
            get_query = "select * from assets where asset_uuid = %s order by last_update desc limit 1"
            get_args = self.kwargs.get("asset_uuid")

        if self.kwargs.get("dbcur", False) is not False:

            found, result = func_query(dbcur=self.kwargs["dbcur"],
                                       query=get_query,
                                       query_args=get_args,
                                       oneonly=True,
                                       failnone=True)

            if found is True:
                # Load Result to Obj
                loaded_good = found

                # Parse JSON Bits
                for json_column in self.__json_columns:
                    if result.get(json_column, None) is not None:
                        result[json_column] = json.loads(result[json_column])
            else:
                self.logger.error("Unable To Load Result from Database")
        else:
            self.logger.error("DBCursor isn't set and needed to do this operation.")

        return loaded_good, result


