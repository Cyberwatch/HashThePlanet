"""
This module handles the resource executions.
"""
from importlib import import_module
from typing import Optional

from loguru import logger

from hashtheplanet.resources.resource import Resource
from hashtheplanet.sql.db_connector import DbConnector


class Executor(): # pylint: disable=too-few-public-methods
    """
    This module handles npm resources to generate hashes.
    """
    def __init__(self, database: DbConnector, session_scope):
        self._database = database
        self._session_scope = session_scope

    def execute(self, resource_name: str, target: str, exclude_regex: Optional[str] = None):
        """
        This method executes a resource to compute hashes.
        """
        resource_path = f"{resource_name}_resource"
        resource_class_name = f"{resource_name.title()}Resource"

        try:
            module = import_module("hashtheplanet.resources." + resource_path)
        except ImportError:
            logger.error(f"[!] Could not find module {resource_path}")
            return

        resource_instance: Resource = getattr(module, resource_class_name)(self._database)
        resource_instance.compute_hashes(self._session_scope, target, exclude_regex)
