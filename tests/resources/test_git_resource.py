"""
Unit tests for GitResource class.
"""
import subprocess

#standard imports
from unittest import mock
from unittest.mock import MagicMock, patch

# project imports
from hashtheplanet.resources.git_resource import GitResource, EMPTY_BLOB_SHA1
from hashtheplanet.builders.json_builder import JsonBuilder


def test_clone_or_fetch_clone():
    """
    Should clone when the repo path doesn't exist.
    """
    with mock.patch("subprocess.check_call") as mock_call, \
         mock.patch("os.path.isdir", return_value=False):
        GitResource.clone_or_fetch("http://foo.bar/foobar.git", "/tmp/foobar.git")
        mock_call.assert_called_once_with(
            ['git', 'clone', '--bare', "http://foo.bar/foobar.git", "/tmp/foobar.git"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


def test_clone_or_fetch_fetch():
    """
    Should fetch when the repo path already exists.
    """
    with mock.patch("subprocess.check_call") as mock_call, \
         mock.patch("os.path.isdir", return_value=True):
        GitResource.clone_or_fetch("http://foo.bar/foobar.git", "/tmp/foobar.git")
        mock_call.assert_called_once_with(
            ['git', 'fetch', '--tags', '--force', 'origin'],
            cwd="/tmp/foobar.git",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )


def test_get_tags():
    """
    Should parse git tag -l output.
    """
    tag_output = b"1.0.0\n1.0.1\n2.0.0\n"
    with mock.patch("subprocess.check_output", return_value=tag_output):
        tags = GitResource.get_tags("/tmp/repo.git")
        assert tags == ["1.0.0", "1.0.1", "2.0.0"]


def test_get_tags_empty():
    """
    Should return empty list for repo with no tags.
    """
    with mock.patch("subprocess.check_output", return_value=b""):
        tags = GitResource.get_tags("/tmp/repo.git")
        assert tags == []


def test_ls_tree():
    """
    Should parse git ls-tree -r output correctly.
    """
    ls_tree_output = (
        "100644 blob d159169d1050894d3ea3b98e1c965c4058208fe1\tLICENSE\n"
        "100644 blob 29a422c19251aeaeb907175e9b3219a9bed6c616\tsrc/app.js\n"
        "100644 blob e42f952edc48e2c085c206166bf4f1ead4d4b058\tsetup.txt\n"
        f"100644 blob {EMPTY_BLOB_SHA1}\tempty.txt\n"
        "100644 blob abcdef1234567890abcdef1234567890abcdef12\ttest.php\n"
    ).encode("utf-8")

    with mock.patch("subprocess.check_output", return_value=ls_tree_output):
        files = GitResource.ls_tree("/tmp/repo.git", "1.0.0")

        # Should have 3 files (empty blob and .php excluded)
        assert len(files) == 3
        assert files[0] == ("LICENSE", "d159169d1050894d3ea3b98e1c965c4058208fe1")
        assert files[1] == ("src/app.js", "29a422c19251aeaeb907175e9b3219a9bed6c616")
        assert files[2] == ("setup.txt", "e42f952edc48e2c085c206166bf4f1ead4d4b058")


def test_ls_tree_error():
    """
    Should return empty list on CalledProcessError.
    """
    with mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "git")):
        files = GitResource.ls_tree("/tmp/repo.git", "bad-tag")
        assert files == []


def test_get_blob_hashes():
    """
    Should collect all file metadata across tags.
    """
    def mock_ls_tree(repo_path, tag_name):
        if tag_name == "1.0":
            return [("LICENSE", "hash1"), ("app.js", "hash2")]
        elif tag_name == "1.1":
            return [("LICENSE", "hash1"), ("app.js", "hash3")]
        return []

    git_resource = GitResource()

    with mock.patch.object(GitResource, "ls_tree", side_effect=mock_ls_tree):
        files = git_resource._get_blob_hashes("/tmp/repo.git", ["1.0", "1.1"])

        assert len(files) == 4
        assert files[0] == ("LICENSE", "1.0", "hash1")
        assert files[1] == ("app.js", "1.0", "hash2")
        assert files[2] == ("LICENSE", "1.1", "hash1")
        assert files[3] == ("app.js", "1.1", "hash3")


def test_get_blob_hashes_skip_tags():
    """
    Should skip tags in the skip set.
    """
    def mock_ls_tree(repo_path, tag_name):
        if tag_name == "1.0":
            return [("LICENSE", "hash1")]
        elif tag_name == "1.1":
            return [("LICENSE", "hash2")]
        return []

    git_resource = GitResource()

    with mock.patch.object(GitResource, "ls_tree", side_effect=mock_ls_tree):
        files = git_resource._get_blob_hashes("/tmp/repo.git", ["1.0", "1.1"], skip_tags={"1.0"})

        assert len(files) == 1
        assert files[0] == ("LICENSE", "1.1", "hash2")


def test_compute_hashes_with_builder():
    """
    Should clone, get tags, get hashes, and save to builder.
    """
    git_resource = GitResource()
    builder = JsonBuilder()

    files = [("LICENSE", "1.0", "hash1"), ("app.js", "1.0", "hash2")]

    with mock.patch.object(GitResource, "clone_or_fetch") as mock_clone, \
         mock.patch.object(GitResource, "get_tags", return_value=["1.0"]) as mock_tags, \
         mock.patch.object(GitResource, "_get_blob_hashes", return_value=files) as mock_hashes, \
         mock.patch("os.makedirs"):
        git_resource.compute_hashes("http://foo.bar/foobar.git", cache_dir="/tmp/cache", builder=builder)

        mock_clone.assert_called_once_with("http://foo.bar/foobar.git", "/tmp/cache/foobar.git")
        mock_tags.assert_called_once()
        mock_hashes.assert_called_once()

    data = builder.get_technology_data("foobar")
    assert "LICENSE" in data
    assert "app.js" in data


def test_compute_hashes_clone_error():
    """
    Should handle clone errors gracefully.
    """
    git_resource = GitResource()
    builder = JsonBuilder()

    with mock.patch.object(GitResource, "clone_or_fetch",
                           side_effect=subprocess.CalledProcessError(1, "git")) as mock_clone, \
         mock.patch("os.makedirs"):
        git_resource.compute_hashes("http://foo.bar/foobar.git", cache_dir="/tmp/cache", builder=builder)

    # Builder should remain empty
    assert builder.get_technologies() == []
