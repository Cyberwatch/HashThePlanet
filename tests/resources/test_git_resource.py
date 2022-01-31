"""
Unit tests for DbConnector class.
"""
import hashlib
import subprocess

#standard imports
from typing import Dict, List, Tuple
from unittest import mock
from unittest.mock import MagicMock, patch

# project imports
from hashtheplanet.resources.git_resource import BlobHash, FilePath, GitResource
from hashtheplanet.sql.db_connector import DbConnector

# third party imports
from git.exc import GitCommandError
from git.objects.commit import Commit


def subprocess_mock(blobs: Dict[str, str]):
    def subprocess_mock(cmd_args, *args, **kwargs):
        for expected_filename, content in blobs.items():
            if cmd_args[3] == expected_filename:
                return blobs[expected_filename]
        raise FileNotFoundError('(mock) Unable to retrieve {cmd_args}')
    return MagicMock(side_effect=subprocess_mock)

def test_clone_repository():
    """
    Should verify if the repository has been clone with the good arguments
    """
    git_resource = GitResource(None)
    repo_url = "http://foo.bar/foobar.git"
    repo_path = "/foobar/"

    with mock.patch("git.Repo.clone_from", return_value=None) as clone_from_mock:
        git_resource.clone_repository(repo_url, repo_path)
        clone_from_mock.assert_called_once_with(repo_url, repo_path, bare=True)

def test_get_all_files_from_commit():
    """
    Unit tests for get_all_files_from_commit method.
    """
    class MockBlob():
        def __init__(self, mode: int, path: str, hexsha: str):
            self.mode = mode
            self.path = path
            self.hexsha = hexsha

    class MockTree():
        def traverse(*args):
            return [
                MockBlob(33188, "LICENSE", "d159169d1050894d3ea3b98e1c965c4058208fe1"),
                MockBlob(16384, "dist", "29a422c19251aeaeb907175e9b3219a9bed6c616"),
                MockBlob(33188, "setup.cfg", "e42f952edc48e2c085c206166bf4f1ead4d4b058"),
            ]

    class MockCommit():
        tree = MockTree()

    git_resource = GitResource(None)

    with patch.object(Commit, 'tree', return_value=MockCommit()) as mock_variable:
        mock_commit = MockCommit()
        files: List[Tuple[FilePath, BlobHash]] = git_resource.get_all_files_from_commit(mock_commit)
        mock_variable.called == True

        assert len(files) == 2
        assert files[0][0] == "LICENSE"
        assert files[0][1] == "d159169d1050894d3ea3b98e1c965c4058208fe1"
        assert files[1][0] == "setup.cfg"
        assert files[1][1] == "e42f952edc48e2c085c206166bf4f1ead4d4b058"

def test_hash_files():
    """
    Unit tests for _hash_files method.
    """
    blobs = {
        "empty_blob": "".encode("utf-8"),
        "d159169d1050894d3ea3b98e1c965c4058208fe1": "license content".encode("utf-8"),
        "e42f952edc48e2c085c206166bf4f1ead4d4b058": "setup.cfg content".encode("utf-8"),
        "empty": ""
    }

    git_files_metadata = [
        ["empty", "1.2.9", "empty_blob"],
        ["LICENSE", "1.2.3", "d159169d1050894d3ea3b98e1c965c4058208fe1"],
        ["setup.cfg", "1.2.5", "e42f952edc48e2c085c206166bf4f1ead4d4b058"],
    ]

    git_resource = GitResource(None)

    with mock.patch("subprocess.check_output", subprocess_mock(blobs)) as sp_mock, \
        mock.patch("os.getcwd", return_value="/foobar/") as getcwd_mock, \
        mock.patch("os.chdir", return_value=None) as chdir_mock:
        files_metadata = git_resource._hash_files(git_files_metadata, "repo_dir_path")

        assert sp_mock.call_count == 3
        sp_mock.assert_called_with(['git', 'cat-file', '-p', 'e42f952edc48e2c085c206166bf4f1ead4d4b058'], shell=False)

        getcwd_mock.assert_called_once()

        assert chdir_mock.call_count == 2
        chdir_mock.assert_called_with("/foobar/")

        assert len(files_metadata) == 2

        assert files_metadata[0][0] == "LICENSE"
        assert files_metadata[0][1] == "1.2.3"
        assert files_metadata[0][2] == hashlib.sha256(blobs.get("d159169d1050894d3ea3b98e1c965c4058208fe1")).hexdigest()

        assert files_metadata[1][0] == "setup.cfg"
        assert files_metadata[1][1] == "1.2.5"
        assert files_metadata[1][2] == hashlib.sha256(blobs.get("e42f952edc48e2c085c206166bf4f1ead4d4b058")).hexdigest()


    with mock.patch("subprocess.check_output", subprocess_mock(blobs)) as sp_mock, \
        mock.patch("os.getcwd", return_value="/foobar/") as getcwd_mock, \
        mock.patch("os.chdir", return_value=None) as chdir_mock:
        files_metadata = git_resource._hash_files([["empty", "1.2.1", "empty"]], "repo_dir_path")

        assert sp_mock.call_count == 1
        sp_mock.assert_called_with(['git', 'cat-file', '-p', 'empty'], shell=False)

        getcwd_mock.assert_called_once()

        assert chdir_mock.call_count == 2
        chdir_mock.assert_called_with("/foobar/")

        assert not len(files_metadata)


    with mock.patch.object(subprocess, "check_output", MagicMock(side_effect=ValueError("error"))) as mock_exec, \
        mock.patch("os.getcwd", return_value="/foobar/") as getcwd_mock, \
        mock.patch("os.chdir", return_value=None) as chdir_mock:
        git_resource._hash_files(git_files_metadata, "repo_dir_path")

        getcwd_mock.assert_called_once()

        assert chdir_mock.call_count == 2
        chdir_mock.assert_called_with("/foobar/")

        mock_exec.assert_called()
        assert mock_exec.call_count == 3


def test_get_changes_between_two_tags():
    """
    Unit tests for _get_changes_between_two_tags method.
    """
    class MockBlob():
        def __init__(self, mode: int, path: str, hexsha: str):
            self.mode = mode
            self.path = path
            self.hexsha = hexsha

    class MockDiff():
        def __init__(self, a_blob: MockBlob, b_blob: MockBlob):
            self.a_blob = a_blob
            self.b_blob = b_blob

    class MockCommit():
        def diff(*args):
            return [
                MockDiff(MockBlob(16384, "dist", "29a422c19251aeaeb907175e9b3219a9bed6c616"), None),
                MockDiff(None, MockBlob(33188, "LICENSE", "d159169d1050894d3ea3b98e1c965c4058208fe1")),
                MockDiff(MockBlob(33188, "setup.cfg", "e42f952edc48e2c085c206166bf4f1ead4d4b058"), None)
            ]

    git_resource = GitResource(None)
    tag_mock = MagicMock()
    tag_mock.commit = MockCommit()
    tag_mock.name = "1.2.3"

    git_files_metadata = git_resource._get_changes_between_two_tags(tag_mock, tag_mock)

    assert len(git_files_metadata) == 2

    assert git_files_metadata[0][0] == "LICENSE"
    assert git_files_metadata[0][1] == "1.2.3"
    assert git_files_metadata[0][2] == "d159169d1050894d3ea3b98e1c965c4058208fe1"

    assert git_files_metadata[1][0] == "setup.cfg"
    assert git_files_metadata[1][1] == "1.2.3"
    assert git_files_metadata[1][2] == "e42f952edc48e2c085c206166bf4f1ead4d4b058"

def test_get_diff_files():
    """
    Unit tests for _get_diff_files method.
    """
    tag_list = ["A", "B", "C"]

    def mock_get_changes_between_two_tags(self, tag_a, tag_b):
        return [[tag_a, tag_b]]

    with patch.object(GitResource, '_get_changes_between_two_tags', mock_get_changes_between_two_tags):
        git_resource = GitResource(None)
        tags_diff = git_resource._get_diff_files(tag_list)

        assert ["A", "B"] in tags_diff
        assert ["B", "C"] in tags_diff

def test_get_tag_files():
    """
    Unit tests for _get_tag_files method.
    """
    def mock_get_all_files_from_commit(*args):
        return [
            ["LICENSE", "d159169d1050894d3ea3b98e1c965c4058208fe1"],
            ["setup.cfg", "e42f952edc48e2c085c206166bf4f1ead4d4b058"]
        ]

    with patch.object(GitResource, 'get_all_files_from_commit', mock_get_all_files_from_commit):
        git_resource = GitResource(None)
        tag_mock = MagicMock()
        tag_mock.name = "1.2.3"

        tag_files = git_resource._get_tag_files(tag_mock)

        assert len(tag_files) == 2
        assert tag_files[0][0] == "LICENSE"
        assert tag_files[0][1] == "1.2.3"
        assert tag_files[0][2] == "d159169d1050894d3ea3b98e1c965c4058208fe1"

        assert tag_files[1][0] == "setup.cfg"
        assert tag_files[1][1] == "1.2.3"
        assert tag_files[1][2] == "e42f952edc48e2c085c206166bf4f1ead4d4b058"

def test_get_diff_versions():
    """
    Unit tests for _get_diff_versions method.
    """
    class MockTag():
        def __init__(self, name: str):
            self.name = name

    first_version = "1.2.3"
    last_version = "1.4"

    versions = [MockTag("1.2.3"), MockTag("1.2.4"), MockTag("1.3"), MockTag("1.4"), MockTag("1.5.0")]

    git_resource = GitResource(None)
    diff_versions = git_resource._get_diff_versions(first_version, last_version, versions)

    assert len(diff_versions) == 3
    assert first_version in diff_versions
    assert "1.2.4" in diff_versions
    assert "1.3" in diff_versions
    assert last_version not in diff_versions

def test_save_hashes(dbsession):
    """
    Unit tests for _get_diff_versions method.
    """
    class MockTag():
        def __init__(self, name: str):
            self.name = name
    def session_scope():
        return dbsession

    db_connector = DbConnector()
    git_resource = GitResource(db_connector)

    files_metadata = [
        ["LICENSE", "1.2.3", "license_hash"],
        ["setup.cfg", "1.2.3", "setup_hash"],
        ["LICENSE", "1.2.4", "license_modified_hash"]
    ]

    tags = [
        MockTag("1.2.3"),
        MockTag("1.2.4")
    ]

    with mock.patch.object(DbConnector, "insert_versions", MagicMock()) as db_insert_v, \
        mock.patch.object(DbConnector, "insert_file", MagicMock()) as db_insert_f, \
        mock.patch.object(DbConnector, "insert_or_update_hash", MagicMock()) as db_insert_h:
        git_resource._save_hashes(session_scope, files_metadata, tags, "foobar")

        db_insert_v.assert_called_once()

        assert db_insert_f.called is True
        assert db_insert_f.call_count == 3

        assert db_insert_h.called is True
        assert db_insert_h.call_count == 4

def test_filter_stored_tags():
    """
    Should test the behavior of tags when some of them are already downloaded
    """

    class MockedTag():
        def __init__(self, name) -> None:
            self.name = name

    git_resource = GitResource(None)
    stored_versions = [
        "A",
        "B",
        "C",
        "D"
    ]
    repository_versions = [
        MockedTag("A"),
        MockedTag("B"),
        MockedTag("C"),
        MockedTag("D"),
        MockedTag("E")
    ]

    result = git_resource._filter_stored_tags(stored_versions, repository_versions)

    # In this situation, we have already downloaded the tags: A, B, C, D
    # and in the repository there are the tags: A, B, C, D, E
    # So we need to download only the tags D and E to make a diff a calculates the hash of the found files
    assert [tag.name for tag in result] == ["D", "E"]

    stored_versions = [
        "A",
        "B",
        "C",
    ]
    repository_versions = [
        MockedTag("B"),
        MockedTag("C"),
        MockedTag("D"),
        MockedTag("E")
    ]

    result = git_resource._filter_stored_tags(stored_versions, repository_versions)

    # In this situation, we have already downloaded the tags: A, B, C
    # and in the repository there are the tags: B, C, D, E
    # We can see that we have the tag A that disapeared from the repository, so we need to recalculate the hash
    # of the files from the the missing tag A to the last one
    assert [tag.name for tag in result] == ["B", "C", "D", "E"]

    stored_versions = [
        "A",
        "B",
        "D",
        "E",
    ]
    repository_versions = [
        MockedTag("A"),
        MockedTag("B"),
        MockedTag("C"),
        MockedTag("D"),
        MockedTag("E")
    ]

    result = git_resource._filter_stored_tags(stored_versions, repository_versions)

    # In this situation, we have already downloaded the tags: A, B, D, E
    # and in the repository there are the tags: A, B, C, D, E
    # We can see that in the repository a tag has been added between all of them
    # So we need to download the tag before the added one and all next to create a diff
    # and calculate the hash of the files
    assert [tag.name for tag in result] == ["B", "C", "D", "E"]

    stored_versions = [
        "A",
    ]
    repository_versions = [
        MockedTag("A"),
    ]

    result = git_resource._filter_stored_tags(stored_versions, repository_versions)

    # In this situation, we have already downloaded the tag: A
    # and in the repository there is the tag: A
    # We can see that we have already downloaded the tag, so we return an empty list
    assert not [tag.name for tag in result]


def test_compute_hashes():
    """
    Unit tests for compute_hashes.
    """
    class MockTag():
        def __init__(self, name: str):
            self.name = name

    repo_url = "http://foo.bar/foobar.git"
    tmp_dir_path = "tmp_dir"
    tags = [MockTag("1.2.3"), MockTag("1.2.4")]

    repo_mock = MagicMock(tags=tags)

    class MockDir():
        def __enter__(self):
            return tmp_dir_path

        def __exit__(self, *args):
            pass

    def mock_tmp_dir():
        return MockDir()

    with patch.object(GitResource, "clone_repository", return_value=repo_mock) as mock_clone_repo, \
        patch.object(GitResource, "_get_tag_files", return_value=[1]) as mock_get_tag_files, \
        patch.object(GitResource, "_filter_stored_tags", return_value=tags) as mock_filter_stored_tags, \
        patch.object(GitResource, "_get_diff_files", return_value=[2]) as mock_get_diff_files, \
        patch.object(GitResource, "_hash_files", return_value="hashed files") as mock_hash_files, \
        patch.object(GitResource, "_save_hashes") as mock_save_hashes, \
        patch.object(DbConnector, "get_versions", return_value=[]) as mock_get_versions, \
        patch("tempfile.TemporaryDirectory", MagicMock(side_effect=mock_tmp_dir)):

        session = MagicMock()
        git_resource = GitResource(DbConnector())

        git_resource.compute_hashes(session, repo_url)

        # In this situation, we verify that by giving a good repo_url & a good tmp_dir_path
        # we download the tags, calculate hash & store them in the database
        mock_clone_repo.assert_called_once_with(repo_url, tmp_dir_path)
        mock_get_versions.assert_called_once()
        mock_get_tag_files.assert_called_once_with(tags[0])
        mock_filter_stored_tags.assert_called_once_with([], tags)
        mock_get_diff_files.assert_called_once_with(tags)
        mock_hash_files.assert_called_once_with([1, 2], tmp_dir_path)
        mock_save_hashes.assert_called_once_with(session, "hashed files", tags, "foobar")

    with patch.object(
        GitResource,
        "clone_repository",
        MagicMock(side_effect=GitCommandError("error"))
    ) as mock_clone_repo, \
    patch("tempfile.TemporaryDirectory", MagicMock(side_effect=mock_tmp_dir)), \
    patch.object(GitResource, "_get_tag_files", return_value=[1]) as mock_get_tag_files, \
    patch.object(GitResource, "_filter_stored_tags", return_value=[1]) as mock_filter_stored_tags, \
    patch.object(GitResource, "_get_diff_files", return_value=[2]) as mock_get_diff_files, \
    patch.object(GitResource, "_hash_files", return_value="hashed files") as mock_hash_files, \
    patch.object(GitResource, "_save_hashes") as mock_save_hashes, \
    patch.object(DbConnector, "get_versions") as mock_get_versions:
        git_resource.compute_hashes(MagicMock(), repo_url)
        mock_clone_repo.assert_called_once_with(repo_url, tmp_dir_path)

        # In this situation, we verify that by giving a wrong repository we stop the function
        mock_get_tag_files.assert_not_called()
        mock_get_diff_files.assert_not_called()
        mock_hash_files.assert_not_called()
        mock_save_hashes.assert_not_called()
