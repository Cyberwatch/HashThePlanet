"""
This module handles the resource executions.
"""
from importlib import import_module

from loguru import logger

from hashtheplanet.resources.resource import Resource


class Executor(): # pylint: disable=too-few-public-methods
    """
    This class dispatches hash computation to the appropriate resource.
    """
    def execute(self, resource_name: str, target: str, **kwargs):
        """
        This method executes a resource to compute hashes.
        Extra kwargs (builder, cache_dir) are forwarded to compute_hashes.
        """
        resource_path = f"{resource_name}_resource"
        resource_class_name = f"{resource_name.title()}Resource"

        try:
            module = import_module("hashtheplanet.resources." + resource_path)
        except ImportError:
            logger.error(f"[!] Could not find module {resource_path}")
            return

        resource_instance: Resource = getattr(module, resource_class_name)()
        resource_instance.compute_hashes(target, **kwargs)
