"""
This module handles the config file.
"""
import json
from json.decoder import JSONDecodeError
from typing import Dict, List
from loguru import logger

from hashtheplanet.resources.git_resource import GitResource
from hashtheplanet.resources.npm_resource import NpmResource

class Config():
    """
    This class implements methods to manipulate the config file.
    """
    def __init__(self):
        self._config = {}
        self.resources_name = [
            GitResource.name,
            NpmResource.name
        ]

    def parse(self, config_path: str):
        """
        This method parses the config file and loads it in the class.
        """
        try:
            with open(config_path, "r", encoding="utf-8") as file_fp:
                self._config = json.load(file_fp)

        except (OSError, JSONDecodeError) as exception:
            logger.error(exception)

    def get_targets(self, resource_name: str) -> List[str]:
        """
        This methods returns the targets used by the given resource.
        """
        module_info: Dict = self._config.get(resource_name)

        if module_info is None:
            return []
        return module_info.get("targets")

    def get_used_resources(self) -> List[str]:
        """
        This method returns the used resources.
        """
        return list(list(set(self._config).intersection(self.resources_name)))
