import json
import os
import sys
import tempfile
from typing import Dict
from unittest import mock
from unittest.mock import MagicMock, mock_open, patch
from loguru import logger
from hashtheplanet.config.config import Config
from hashtheplanet.resources.git_resource import GitResource
from hashtheplanet.builders.json_builder import JsonBuilder

from hashtheplanet.core.hashtheplanet import HashThePlanet, main

def get_mock_open(files: Dict[str, str]):
    def open_mock(filename, *args, **kwargs):
        for expected_filename, content in files.items():
            if filename == expected_filename:
                return mock_open(read_data=content).return_value
        raise FileNotFoundError(f'(mock) Unable to open {filename}')
    return MagicMock(side_effect=open_mock)

def test_htp_constructor():
    """
    Unit tests for constructor.
    """
    htp = HashThePlanet("input.json", json_dir="/tmp/json", cache_dir="/tmp/cache", max_workers=2)

    assert htp._input_file == "input.json"
    assert htp._json_dir == "/tmp/json"
    assert htp._cache_dir == "/tmp/cache"
    assert htp._max_workers == 2
    assert htp._discrimination_threshold == 0.05


def test_htp_constructor_custom_threshold():
    """
    The discrimination threshold can be overridden.
    """
    htp = HashThePlanet("input.json", discrimination_threshold=0.1)
    assert htp._discrimination_threshold == 0.1


def test_compute_hashes():
    files = {
        "foobar.txt": """
        {
            "$schema": "./schema.json",
            "git": {
                "targets": [
                    "https://github.com/silexphp/Silex.git"
                ]
            },
            "npm": {
                "targets": [
                ]
            }
        }
        """,
        "empty.txt": "\n"
    }

    with mock.patch("builtins.open", get_mock_open(files)) as mock_file_open, \
        mock.patch.object(GitResource, "compute_hashes", return_value=None) as mock_compute_hashes, \
        mock.patch.object(JsonBuilder, "save_json") as mock_save, \
        mock.patch("os.path.isdir", return_value=False):
        htp = HashThePlanet("foobar.txt")
        htp.compute_hashs()

        mock_file_open.assert_called_once_with("foobar.txt", "r", encoding="utf-8")
        mock_compute_hashes.assert_called_once()
        mock_save.assert_called_once()

    with mock.patch("builtins.open", get_mock_open(files)) as mock_file_open, \
        mock.patch("os.path.isdir", return_value=False):
        htp = HashThePlanet("empty.txt")
        try:
            htp.compute_hashs()
        except SystemExit as e:
            assert e.code == 1
            mock_file_open.assert_called_once_with("empty.txt", "r", encoding="utf-8")
        else:
            assert False

    with mock.patch.object(Config, "parse", MagicMock(side_effect=OSError("error"))) as mock_parse, \
        mock.patch.object(logger, "error") as mock_error_logger:

        htp = HashThePlanet("foobar.txt")

        try:
            htp.compute_hashs()
        except SystemExit as e:
            assert e.code == 1
            mock_error_logger.assert_called_once()
        else:
            assert False


def test_find_hash():
    """
    Test find_hash searches in JSON files (legacy format).
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Create a legacy format test JSON file
        data = {
            "wp-admin/css/about.css": {
                "abc123": ["4.5", "4.5.1"],
                "def456": ["4.6"]
            }
        }
        with open(os.path.join(tmp_dir, "wordpress_hash_files.json"), "w") as f:
            json.dump(data, f)

        htp = HashThePlanet("input.json", json_dir=tmp_dir)

        # Found
        result = htp.find_hash("abc123")
        assert result[0] == "wordpress"
        assert result[1] == ["4.5", "4.5.1"]

        # Not found
        result = htp.find_hash("nonexistent")
        assert result == (None, None)


def test_find_hash_v2_format():
    """
    Test find_hash works with v2 JSON format (with ranges).
    """
    with tempfile.TemporaryDirectory() as tmp_dir:
        data = {
            "_meta": {
                "format_version": 2,
                "sorted_versions": ["4.5", "4.5.1", "4.6"]
            },
            "files": {
                "wp-admin/css/about.css": {
                    "abc123": ["4.5-4.5.1"],
                    "def456": ["4.6"]
                }
            }
        }
        with open(os.path.join(tmp_dir, "wordpress_hash_files.json"), "w") as f:
            json.dump(data, f)

        htp = HashThePlanet("input.json", json_dir=tmp_dir)

        result = htp.find_hash("abc123")
        assert result[0] == "wordpress"
        assert sorted(result[1]) == ["4.5", "4.5.1"]

        result = htp.find_hash("def456")
        assert result[0] == "wordpress"
        assert result[1] == ["4.6"]


def test_main():
    def return_magic_mock(*args):
        return MagicMock()

    with mock.patch('sys.argv', ["/foobar/"]), \
        patch.object(HashThePlanet, "compute_hashs", return_magic_mock()) as mock_compute_hash:
        main()
        mock_compute_hash.assert_called_once()

    with mock.patch('sys.argv', ["/foobar/", "--color"]), \
        patch.object(HashThePlanet, "compute_hashs", return_magic_mock()) as mock_compute_hash:
        main()
        mock_compute_hash.assert_called_once()

    with mock.patch('sys.argv', ["/foobar/", "--hash", "super_hash"]), \
        patch.object(HashThePlanet, "compute_hashs", return_magic_mock()) as mock_compute_hash, \
        patch.object(HashThePlanet, "find_hash", return_magic_mock()) as mock_find_hash:
        main()

        mock_compute_hash.assert_not_called()
        mock_find_hash.assert_called_once()
        mock_find_hash.assert_called_once_with("super_hash")

    with mock.patch('sys.argv', ["/foobar/", "--file", "license.txt"]), \
        patch.object(HashThePlanet, "compute_hashs", return_magic_mock()) as mock_compute_hash, \
        mock.patch("hashtheplanet.core.hashtheplanet.calculate_git_hash", return_value="super_hash") as mock_git_hash, \
        patch.object(HashThePlanet, "find_hash", return_magic_mock()) as mock_find_hash:
        main()

        mock_git_hash.assert_called_once_with("license.txt")
        mock_find_hash.assert_called_once_with("super_hash")
        mock_compute_hash.assert_not_called()

    with mock.patch('sys.argv', ["/foobar/", "--file", "license.txt"]), \
        patch.object(HashThePlanet, "compute_hashs", return_magic_mock()) as mock_compute_hash, \
        mock.patch("hashtheplanet.core.hashtheplanet.calculate_git_hash", return_value=None) as mock_git_hash, \
        patch.object(HashThePlanet, "find_hash", return_magic_mock()) as mock_find_hash:
        main()

        mock_git_hash.assert_called_once_with("license.txt")
        mock_find_hash.assert_not_called()
        mock_compute_hash.assert_not_called()
