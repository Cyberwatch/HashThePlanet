"""
This module contains the base class for the resources.
"""
from hashtheplanet.sql.db_connector import DbConnector

class Resource(): # pylint: disable=too-few-public-methods
    """
    This class is the base class for all the resources.
    """
    name = "N/A"

    def __init__(self, database: DbConnector):
        self._database = database

    def compute_hashes(self, session_scope, target: str):
        """
        This method computes all the versions and their associated files & hashes and stores them in the database.
        """
        raise NotImplementedError()
