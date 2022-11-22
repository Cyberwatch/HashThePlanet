"""
This module contains the base class for the resources.
"""
import re
from typing import Optional

from hashtheplanet.sql.db_connector import DbConnector

class Resource(): # pylint: disable=too-few-public-methods
    """
    This class is the base class for all the resources.
    """
    name = "N/A"

    def __init__(self, database: DbConnector):
        self._database = database

    def compute_hashes(self, session_scope, target: str, exclude_regex: Optional[str]):
        """
        This method computes all the versions and their associated files & hashes and stores them in the database.
        """
        raise NotImplementedError()

    @staticmethod
    def should_save(exclude_regex: str, file_path: str):
        """
        This method permits to verify if the specified file should be saved in the database or not
        """
        if not file_path:
            return False
        if not exclude_regex:
            return True
        return not re.search(exclude_regex, file_path)
