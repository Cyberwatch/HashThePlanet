"""
This module handles the config file.
"""
from enum import Enum
import json
from typing import Dict, List

from hashtheplanet.resources.git_resource import GitResource
from hashtheplanet.resources.npm_resource import NpmResource

class ConfigField(Enum):
    """
    This enum contains every field that can be found in the config file
    """
    TARGETS = "targets"
    EXCLUDE_REGEX = "exclude_regex"

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
        with open(config_path, "r", encoding="utf-8") as file_fp:
            self._config = json.load(file_fp)

    def get(self, resource_name: str, config_field: ConfigField):
        """
        This methods returns a field content used by the given resource.
        """
        field_content: Dict = self._config.get(resource_name)

        if not config_field or not field_content:
            return None
        return field_content.get(config_field.value)

    def get_used_resources(self) -> List[str]:
        """
        This method returns the used resources.
        """
        return list(list(set(self._config).intersection(self.resources_name)))
