"""
Unit tests for hash utility functions.
"""
import hashlib
from unittest import mock
from unittest.mock import MagicMock

from hashtheplanet.utils.hash_utils import hash_bytes, calculate_git_hash


def test_hash_bytes():
    data = b"hello world"
    expected = hashlib.sha256(data).hexdigest()
    assert hash_bytes(data) == expected


def test_hash_bytes_empty():
    data = b""
    expected = hashlib.sha256(data).hexdigest()
    assert hash_bytes(data) == expected


def test_calculate_git_hash():
    with mock.patch("subprocess.check_output", return_value=b"abc123def456\n"):
        result = calculate_git_hash("/tmp/test.txt")
        assert result == "abc123def456"


def test_calculate_git_hash_error():
    import subprocess
    with mock.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "git")):
        result = calculate_git_hash("/tmp/nonexistent.txt")
        assert result is None
