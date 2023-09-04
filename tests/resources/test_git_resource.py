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
from git import Tag


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
                MockBlob(16384, "dist.js", "29a422c19251aeaeb907175e9b3219a9bed6c616"),
                MockBlob(33188, "setup.txt", "e42f952edc48e2c085c206166bf4f1ead4d4b058"),
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
        assert files[1][0] == "setup.txt"
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
        git_resource._save_hashes(session_scope, files_metadata, "foobar")

        assert db_insert_h.called is True
        assert db_insert_h.call_count == 3

def test_compute_hashes():
    """
    Unit tests for compute_hashes.
    """

    files = [('LICENSE', '1.2.3', 'd159169d1050894d3ea3b98e1c965c4058208fe1'),
             ('dist.js', '1.2.3', '29a422c19251aeaeb907175e9b3219a9bed6c616'),
             ('setup.txt', '1.2.3', 'e42f952edc48e2c085c206166bf4f1ead4d4b058'),
             ('LICENSE', '1.2.4', 'd159169d1050894d3ea3b98e1c965c4058208fe1'),
             ('dist.js', '1.2.4', '29a422c19251aeaeb907175e9b3219a9bed6c616'),
             ('setup.txt', '1.2.4', 'e42f952edc48e2c085c206166bf4f1ead4d4b058')]
    class MockTree():
        def traverse(*args):
            return [
                MockBlob(33188, "LICENSE", "d159169d1050894d3ea3b98e1c965c4058208fe1", "blob"),
                MockBlob(16384, "dist.js", "29a422c19251aeaeb907175e9b3219a9bed6c616", "blob"),
                MockBlob(33188, "setup.txt", "e42f952edc48e2c085c206166bf4f1ead4d4b058", "blob"),
            ]
    class MockBlob():
        def __init__(self, mode: int, path: str, hexsha: str, type : str):
            self.mode = mode
            self.path = path
            self.hexsha = hexsha
            self.type = type
    class MockDiff():
        def __init__(self, a_blob: MockBlob, b_blob: MockBlob):
            self.a_blob = a_blob
            self.b_blob = b_blob
    class MockCommit():
        tree =MockTree()
    class MockTag():
        def __init__(self, name: str, commit: MockCommit):
            self.name = name
            self.commit = MockCommit()

    repo_url = "http://foo.bar/foobar.git"
    tmp_dir_path = "tmp_dir"
    tags = [MockTag("1.2.3", MockCommit()), MockTag("1.2.4", MockCommit)]

    repo_mock = MagicMock(tags=tags)

    class MockDir():
        def __enter__(self):
            return tmp_dir_path

        def __exit__(self, *args):
            pass

    def mock_tmp_dir():
        return MockDir()


    with patch.object(GitResource, "clone_repository", return_value=repo_mock) as mock_clone_repo, \
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
        mock_save_hashes.assert_called_once_with(session, files, "foobar")

    with patch.object(
        GitResource,
        "clone_repository",
        MagicMock(side_effect=GitCommandError("error"))
    ) as mock_clone_repo, \
    patch("tempfile.TemporaryDirectory", MagicMock(side_effect=mock_tmp_dir)), \
    patch.object(GitResource, "_hash_files", return_value="hashed files") as mock_hash_files, \
    patch.object(GitResource, "_save_hashes") as mock_save_hashes, \
    patch.object(DbConnector, "get_versions") as mock_get_versions:
        git_resource.compute_hashes(MagicMock(), repo_url)
        mock_clone_repo.assert_called_once_with(repo_url, tmp_dir_path)

        # In this situation, we verify that by giving a wrong repository we stop the function
        mock_hash_files.assert_not_called()
        mock_save_hashes.assert_not_called()
