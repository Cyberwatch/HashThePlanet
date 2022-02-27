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
        resource.compute_hashes(None, None, None)
        assert False
    except NotImplementedError as error:
        assert True

def test_should_save():
    resource = Resource("test")

    assert resource.should_save(".php", "test.php") is False
    assert resource.should_save(".js", "test.php") is True
    assert resource.should_save("^tests/", "tests/foobar.js") is False

def test_should_save_none():
    resource = Resource("test")

    assert resource.should_save(None, "test.php") is True
    assert resource.should_save(".js", None) is False
    assert resource.should_save(None, None) is False
