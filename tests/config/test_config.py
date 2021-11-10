"""
Unit tests for Config class.
"""
#standard imports
from typing import Dict
from unittest import mock
from unittest.mock import MagicMock, mock_open, patch

# project imports
from hashtheplanet.config.config import Config

def get_mock_open(files: Dict[str, str]):
    def open_mock(filename, *args, **kwargs):
        for expected_filename, content in files.items():
            if filename == expected_filename:
                return mock_open(read_data=content).return_value
        raise FileNotFoundError('(mock) Unable to open {filename}')
    return MagicMock(side_effect=open_mock)

def test_parse():
    """
    Unit tests for parse method.
    """
    files = {
        "tech_list.json": '{"git": {"targets": ["https://foo/bar.git"]}, "npm": {"targets": ["foobar"]}}',
        "wrongly_formatted.json": "wrongly formatted"
    }
    config = Config()

    with mock.patch("builtins.open", get_mock_open(files)) as mock_open:
        config.parse("tech_list.json")
        assert mock_open.called is True
        assert mock_open.call_count == 1
        assert config._config is not None

    config._config = {}

    with mock.patch("builtins.open", get_mock_open(files)) as mock_open:
        config.parse("wrongly_formatted.json")
        assert mock_open.called is True
        assert mock_open.call_count == 1
        assert len(config._config) == 0

    config._config = {}

    with mock.patch("builtins.open", MagicMock(side_effect=OSError("error"))) as mock_open:
        config.parse("tech_list.json")
        assert mock_open.called is True
        assert mock_open.call_count == 1
        assert len(config._config) == 0

def test_get_targets():
    """
    Unit tests for get_targets method.
    """
    config = Config()

    with patch.dict(config._config, {"git": {"targets": ["target1", "target2"]}}):
        assert len(config.get_targets("git")) == 2

        assert len(config.get_targets("npm")) == 0

def test_get_used_resources():
    config = Config()

    with patch.dict(config._config, {"git": {"targets": ["target1", "target2"]}}):
        assert len(config.get_used_resources()) == 1

    with patch.dict(config._config, {"git": {"targets": ["target1", "target2"]}, "npm": {"targets": ["jquery"]}}):
        assert len(config.get_used_resources()) == 2
