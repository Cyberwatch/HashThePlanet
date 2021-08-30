"""
Unit tests for DbConnector class.
"""
#standard imports
from json import JSONEncoder

# third party imports

# project imports
from lib.sql.db_connector import DbConnector, Tag, File, Hash

def test_insert_tag(dbsession):
    """
    Unit tests for insert_tag method.
    """

    techno = "jQuery"
    tag = "1.2.3"

    DbConnector.insert_tag(dbsession, techno, tag)

    inserted_tag = dbsession.query(Tag).first()
    assert inserted_tag.technology == techno
    assert inserted_tag.tag == tag


def test_insert_tag_already_added_tag(dbsession):
    """
    Unit tests for insert_tag method.
    If techno was already added with this tag,
    it ensures that the tag is not added again.
    """

    techno = "jQuery"
    tag = "1.2.3"

    DbConnector.insert_tag(dbsession, techno, tag)
    DbConnector.insert_tag(dbsession, techno, tag)
    # tag already added before
    assert dbsession.query(Tag).count() == 1


def test_insert_tags(dbsession):
    """
    Unit tests for insert_tags method.
    """

    techno = "jQuery"
    tags = ["1.2.3", "1.3.4", "1.3.5"]

    DbConnector().insert_tags(dbsession, techno, tags)

    inserted_tags = dbsession.query(Tag)
    assert inserted_tags.count() == 3
    for idx, _ in enumerate(inserted_tags):
        assert inserted_tags[idx].technology == techno
        assert inserted_tags[idx].tag == tags[idx]


def test_get_tags(dbsession):
    """
    Unit tests for get_tags method.
    """

    techno = "jQuery"
    tags = ["1.2.3", "1.3.4"]

    dbsession.add(Tag(technology=techno, tag=tags[0]))
    dbsession.add(Tag(technology=techno, tag=tags[1]))

    retrieved_tags = DbConnector.get_tags(dbsession, techno)
    assert len(retrieved_tags) == 2
    for idx, _ in enumerate(retrieved_tags):
        assert retrieved_tags[idx].technology == techno
        assert retrieved_tags[idx].tag == tags[idx]


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
