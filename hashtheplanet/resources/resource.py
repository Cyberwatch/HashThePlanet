"""
This module contains the base class for the resources.
"""


class Resource(): # pylint: disable=too-few-public-methods
    """
    This class is the base class for all the resources.
    """
    name = "N/A"

    def compute_hashes(self, target: str, **kwargs):
        """
        This method computes all the versions and their associated files & hashes.
        """
        raise NotImplementedError()
