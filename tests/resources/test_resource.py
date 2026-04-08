"""
Unit tests for Resource class.
"""
# project imports
from hashtheplanet.resources.resource import Resource

def test_constructor():
    """
    Unit tests for test_constructor method.
    """
    resource = Resource()

    assert resource.name == "N/A"

def test_compute_hashes():
    resource = Resource()

    try:
        resource.compute_hashes(None)
        assert False
    except NotImplementedError as error:
        assert True
