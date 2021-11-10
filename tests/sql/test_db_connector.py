"""
Unit tests for DbConnector class.
"""
#standard imports
from json import JSONEncoder

# third party imports

# project imports
from lib.sql.db_connector import DbConnector, Version, File, Hash

def test_insert_version(dbsession):
    """
    Unit tests for insert_version method.
    """

    techno = "jQuery"
    version = "1.2.3"

    DbConnector.insert_version(dbsession, techno, version)

    inserted_version = dbsession.query(Version).first()
    assert inserted_version.technology == techno
    assert inserted_version.version == version


def test_insert_version_already_added_version(dbsession):
    """
    Unit tests for insert_version method.
    If techno was already added with this version,
    it ensures that the version is not added again.
    """

    techno = "jQuery"
    version = "1.2.3"

    DbConnector.insert_version(dbsession, techno, version)
    DbConnector.insert_version(dbsession, techno, version)
    # version already added before
    assert dbsession.query(Version).count() == 1


def test_insert_versions(dbsession):
    """
    Unit tests for insert_versions method.
    """

    techno = "jQuery"
    versions = ["1.2.3", "1.3.4", "1.3.5"]

    DbConnector().insert_versions(dbsession, techno, versions)

    inserted_versions = dbsession.query(Version)
    assert inserted_versions.count() == 3
    for idx, _ in enumerate(inserted_versions):
        assert inserted_versions[idx].technology == techno
        assert inserted_versions[idx].version == versions[idx]


def test_get_versions(dbsession):
    """
    Unit tests for get_versions method.
    """

    techno = "jQuery"
    versions = ["1.2.3", "1.3.4"]

    dbsession.add(Version(technology=techno, version=versions[0]))
    dbsession.add(Version(technology=techno, version=versions[1]))

    retrieved_versions = DbConnector.get_versions(dbsession, techno)
    assert len(retrieved_versions) == 2
    for idx, _ in enumerate(retrieved_versions):
        assert retrieved_versions[idx].technology == techno
        assert retrieved_versions[idx].version == versions[idx]


def test_insert_file(dbsession):
    """
    Unit tests for insert_file method.
    """

    techno = "jQuery"
    path = "/src/jquery.min.js"

    DbConnector.insert_file(dbsession, techno, path)

    inserted_file = dbsession.query(File).first()
    assert inserted_file.technology == techno
    assert inserted_file.path == path

    DbConnector.insert_file(dbsession, techno, path)
    # file already added before
    assert dbsession.query(File).count() == 1


def test_insert_or_update_hash(dbsession):
    """
    Unit tests for insert_or_update_hash method.
    """

    hash_value = "ab78a59a6f2fbacdceb42bc4b6f1aeff0445d119a83128a20786d34bc3f64527"
    techno = "jQuery"
    versions = ["1.2.3", "1.3.4"]

    DbConnector.insert_or_update_hash(dbsession, hash_value, techno, versions[0])

    inserted_hash = dbsession.query(Hash).first()
    assert inserted_hash.hash == hash_value
    assert inserted_hash.technology == techno
    assert inserted_hash.versions == JSONEncoder().encode({"versions": [versions[0]]})


def test_insert_or_update_hash_already_added_hash(dbsession):
    """
    Unit tests for insert_or_update_hash method.
    If hash was already added with another version,
    it ensures that the new version is added for this hash.
    """

    hash_value = "ab78a59a6f2fbacdceb42bc4b6f1aeff0445d119a83128a20786d34bc3f64527"
    techno = "jQuery"
    versions = ["1.2.3", "1.3.4"]

    DbConnector.insert_or_update_hash(dbsession, hash_value, techno, versions[0])
    DbConnector.insert_or_update_hash(dbsession, hash_value, techno, versions[1])
    # hash already added but not this version
    inserted_hash = dbsession.query(Hash)
    assert inserted_hash.count() == 1
    assert inserted_hash[0].versions == JSONEncoder().encode({"versions": versions})


def test_insert_or_update_hash_already_added_hash_and_version(dbsession):
    """
    Unit tests for insert_or_update_hash method.
    If hash was already added with this version,
    it ensures that the version is not added again for this hash.
    """

    hash_value = "ab78a59a6f2fbacdceb42bc4b6f1aeff0445d119a83128a20786d34bc3f64527"
    techno = "jQuery"
    versions = ["1.2.3", "1.3.4"]

    DbConnector.insert_or_update_hash(dbsession, hash_value, techno, versions[0])
    DbConnector.insert_or_update_hash(dbsession, hash_value, techno, versions[1])
    DbConnector.insert_or_update_hash(dbsession, hash_value, techno, versions[1])
    # hash and version already added
    inserted_hash = dbsession.query(Hash)
    assert inserted_hash.count() == 1
    assert inserted_hash[0].versions == JSONEncoder().encode({"versions": versions})


def test_get_all_hashs(dbsession):
    """
    Unit tests for get_all_hashs method.
    """

    hashs = ["abcdef0123456789", "0123456789abcdef"]
    techno = "jQuery"
    versions = ["1.2.3", "1.3.4"]

    dbsession.add(Hash(hash=hashs[0], technology=techno, versions=JSONEncoder() \
                .encode({"versions": [versions[0]]})))
    dbsession.add(Hash(hash=hashs[1], technology=techno, versions=JSONEncoder() \
                .encode({"versions": [versions[1]]})))

    retrieved_hashs = DbConnector.get_all_hashs(dbsession)
    assert len(retrieved_hashs) == 2
    for idx, _ in enumerate(retrieved_hashs):
        assert retrieved_hashs[idx].hash == hashs[idx]
        assert retrieved_hashs[idx].technology == techno
        assert retrieved_hashs[idx].versions == JSONEncoder().encode({"versions": [versions[idx]]})
