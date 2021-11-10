"""
Unit tests for Resource class.
"""
# project imports
from hashtheplanet.resources.resource import Resource

def test_constructor():
    """
    Unit tests for test_constructor method.
    """
    resource = Resource("database")

    assert resource._database == "database"
    assert resource.name == "N/A"

def test_compute_hashes():
    resource = Resource("database")

    try:
        resource.compute_hashes(None, None)
        assert False
    except NotImplementedError as error:
        assert True
