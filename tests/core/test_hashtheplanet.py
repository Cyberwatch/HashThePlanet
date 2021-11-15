
from typing import Dict
from unittest import mock
from unittest.mock import MagicMock, mock_open, patch
from loguru import logger
from resources.git_resource import GitResource

from sql.db_connector import DbConnector, Hash
from sqlalchemy.engine.base import Engine
from sqlalchemy.orm.session import Session

from hashtheplanet.core.hashtheplanet import HashThePlanet, main

def get_mock_open(files: Dict[str, str]):
    def open_mock(filename, *args, **kwargs):
        for expected_filename, content in files.items():
            if filename == expected_filename:
                return mock_open(read_data=content).return_value
        raise FileNotFoundError('(mock) Unable to open {filename}')
    return MagicMock(side_effect=open_mock)

def test_htp_constructor():
    """
    Unit tests for clone_repository method.
    """
    output_file = "output.db"
    input_file = "input.csv"

    def mock_function_create_engine(url: str):
        assert url == f"sqlite:///{output_file}"
        return "engine_instance"

    def mock_function_sessionmaker(engine):
        assert engine == "engine_instance"

    def mock_function_path_exists(path):
        assert path == output_file
        return False

    with mock.patch("sqlalchemy.create_engine", mock_function_create_engine) as mock_create_engine, \
        mock.patch("sqlalchemy.orm.sessionmaker", mock_function_sessionmaker) as mock_session_maker, \
        mock.patch("os.path.exists", mock_function_path_exists), \
        mock.patch("sqlalchemy.ext.declarative.declarative_base", return_value=MagicMock()):
        htp = HashThePlanet("output.db", "input.csv")

        assert htp._input_file == input_file
        assert htp._output_file == output_file

def test_session_scope():
    """
    Unit tests for session_scope method.
    """
    htp = HashThePlanet("output.db", "input.csv")

    with mock.patch.object(Session, "commit", return_value=None) as mock_commit, \
        mock.patch.object(Session, "close", return_value=None) as mock_close, \
        mock.patch.object(Session, "rollback", return_value=None) as mock_rollback:
        with htp.session_scope() as session:
            mock_commit.assert_not_called()
        mock_commit.assert_called_once_with()

        mock_close.assert_called_once_with()

        mock_rollback.assert_not_called()

        mock_commit.reset_mock()
        mock_close.reset_mock()
        mock_rollback.reset_mock()
        try:
            with htp.session_scope() as session:
                raise Exception()
        except:
            mock_commit.assert_not_called()

            mock_rollback.assert_called_once_with()

            mock_close.assert_called_once_with()


def test_close():
    htp = HashThePlanet("output.db", "input.csv")

    with mock.patch.object(Engine, "dispose") as mock_close:
        htp.close()
        mock_close.assert_called_once_with()

def test_show_all_hashs():
    htp = HashThePlanet("output.db", "input.csv")

    with mock.patch.object(DbConnector, "get_all_hashs", return_value=["hash1", "hash2"]) as mock_get_all_hashes, \
        mock.patch.object(logger, "success") as mock_success_logger, \
        mock.patch.object(logger, "info") as mock_info_logger:
        htp.show_all_hashs()
        mock_get_all_hashes.assert_called_once()

        assert mock_success_logger.called is True
        assert mock_success_logger.call_count == 2

        mock_info_logger.assert_not_called()

    with mock.patch.object(DbConnector, "get_all_hashs", return_value=None) as mock_get_all_hashes, \
        mock.patch.object(logger, "success") as mock_success_logger, \
        mock.patch.object(logger, "info") as mock_info_logger:
        htp.show_all_hashs()

        mock_get_all_hashes.assert_called_once()

        mock_success_logger.assert_not_called()

        mock_info_logger.assert_called_once()

def test_find_hash():
    with mock.patch.object(DbConnector, "find_hash", return_value=("jQuery", {"versions": ["1.3.4"]})) as find_hash_mock:
        htp = HashThePlanet("output.txt", "input.txt")
        htp._session = MagicMock()

        htp.find_hash("hash")
        find_hash_mock.assert_called_once()

def test_compute_hashs():
    files = {
        "foobar.txt": "https://foo.bar/foobar.git",
        "empty.txt": "\n"
    }
    with mock.patch("builtins.open", get_mock_open(files)) as mock_open, \
        mock.patch.object(GitResource, "clone_checkout_and_compute_hashs", return_value=None) as mock_clone_checkout:
        htp = HashThePlanet("output.txt", "foobar.txt")
        htp.compute_hashs()

        mock_open.assert_called_once_with("foobar.txt", "r", encoding="utf-8", newline="")
        mock_clone_checkout.assert_called_once()

        mock_open.reset_mock()
        mock_clone_checkout.reset_mock()

        htp = HashThePlanet("output.txt", "empty.txt")
        htp.compute_hashs()

        mock_open.assert_called_once_with("empty.txt", "r", encoding="utf-8", newline="")
        mock_clone_checkout.assert_not_called()

    with mock.patch("builtins.open", MagicMock(side_effect=OSError("error"))) as mock_open, \
        mock.patch.object(logger, "error") as mock_error_logger:
        htp = HashThePlanet("output.txt", "foobar.txt")
        htp.compute_hashs()

        mock_open.assert_called_once_with("foobar.txt", "r", encoding="utf-8", newline="")
        mock_error_logger.assert_called_once()

def test_analyze_file():
    foobar_hash = "27dd147c7347026fe21b432a2297303bb9990462d886e55facda103598c687fc"
    foobar_technology = "foobar"
    foobar_version = '{"versions": ["1.3.4"]}'
    files = {
        "good_hash.txt": "foobar content".encode("utf-8"),
        "wrong_hash.txt": "wrong_hash content".encode("utf-8")
    }
    class MockDatabase():
        def find_hash(self, session_scope, hash_str: str):
            if hash_str == foobar_hash:
                return (foobar_technology, foobar_version)
            else:
                return (None, None)

    with mock.patch("builtins.open", get_mock_open(files)):
        htp = HashThePlanet("output.txt", "foobar.txt")

        htp.session_scope = MagicMock()
        htp._database = MockDatabase()

        (technology, version) = htp.analyze_file("good_hash.txt")

        assert technology is not None and technology == foobar_technology
        assert version is not None and version == foobar_version

        (technology, version) = htp.analyze_file("wrong_hash.txt")

        assert technology is None
        assert version is None

        (technology, version) = htp.analyze_file(None)

        assert technology is None
        assert version is None

def test_analyze_str():
    foobar_hash = "27dd147c7347026fe21b432a2297303bb9990462d886e55facda103598c687fc"
    foobar_technology = "foobar"
    foobar_version = '{"versions": ["1.3.4"]}'
    good_str = "foobar content"
    wrong_str = "wrong_str content"

    class MockDatabase():
        def find_hash(self, session_scope, hash_str: str):
            if hash_str == foobar_hash:
                return (foobar_technology, foobar_version)
            else:
                return (None, None)
    htp = HashThePlanet("output.txt", "foobar.txt")

    htp.session_scope = MagicMock()
    htp._database = MockDatabase()

    (technology, version) = htp.analyze_str(good_str)
    assert technology is not None and technology == foobar_technology
    assert version is not None and version == foobar_version

    (technology, version) = htp.analyze_str(wrong_str)

    assert technology is None
    assert version is None

    (technology, version) = htp.analyze_str(None)

    assert technology is None
    assert version is None

def test_analyze_hash():
    foobar_hash = "27dd147c7347026fe21b432a2297303bb9990462d886e55facda103598c687fc"
    foobar_technology = "foobar"
    foobar_version = '{"versions": ["1.3.4"]}'
    good_hash = "27dd147c7347026fe21b432a2297303bb9990462d886e55facda103598c687fc"
    wrong_hash = "261fb41cc56396fc54f70fd26cf4324d0baaf0092e900c064693e24a297f63fc"

    class MockDatabase():
        def find_hash(self, session_scope, hash_str: str):
            if hash_str == foobar_hash:
                return (foobar_technology, foobar_version)
            else:
                return (None, None)
    htp = HashThePlanet("output.txt", "foobar.txt")

    htp.session_scope = MagicMock()
    htp._database = MockDatabase()

    (technology, version) = htp.analyze_hash(good_hash)
    assert technology is not None and technology == foobar_technology
    assert version is not None and version == foobar_version

    (technology, version) = htp.analyze_hash(wrong_hash)

    assert technology is None
    assert version is None

    (technology, version) = htp.analyze_hash(None)

    assert technology is None
    assert version is None

def test_get_static_files():
    class MockDatabase():
        def get_static_files(self, session_scope):
            return ["license.txt", "README.md"]
    htp = HashThePlanet("output.txt", "foobar.txt")

    htp.session_scope = MagicMock()
    htp._database = MockDatabase()

    static_files = htp.get_static_files()
    assert len(static_files) == 2

def test_main():
    def return_magic_mock(*args):
        return MagicMock()

    with mock.patch('sys.argv', ["/foobar/"]), \
        patch.object(HashThePlanet, "compute_hashs", return_magic_mock()) as mock_compute_hash, \
        patch.object(HashThePlanet, "show_all_hashs", return_magic_mock()) as mock_show_hashes, \
        patch.object(HashThePlanet, "close", return_magic_mock()) as mock_close:
        main()

        mock_compute_hash.assert_called_once()
        mock_show_hashes.assert_called_once()
        mock_close.assert_called_once()

    with mock.patch('sys.argv', ["/foobar/", "--color"]), \
        patch.object(HashThePlanet, "compute_hashs", return_magic_mock()) as mock_compute_hash, \
        patch.object(HashThePlanet, "show_all_hashs", return_magic_mock()) as mock_show_hashes, \
        patch.object(HashThePlanet, "close", return_magic_mock()) as mock_close:
        main()

        mock_compute_hash.assert_called_once()
        mock_show_hashes.assert_called_once()
        mock_close.assert_called_once()

    with mock.patch('sys.argv', ["/foobar/", "--file", "license.txt"]), \
        patch.object(HashThePlanet, "compute_hashs", return_magic_mock()) as mock_compute_hash, \
        patch.object(Hash, "hash_file", return_value="super hash") as mock_hash_find_hash, \
        patch.object(HashThePlanet, "find_hash", return_magic_mock()) as mock_htp_find_hash:
        main()

        mock_hash_find_hash.assert_called_once()
        mock_htp_find_hash.assert_called_once()
        mock_hash_find_hash.assert_called_once_with("license.txt")
        mock_htp_find_hash.assert_called_once_with("super hash")
        mock_compute_hash.assert_not_called()

    with mock.patch('sys.argv', ["/foobar/", "--file", "license.txt"]), \
        patch.object(HashThePlanet, "compute_hashs", return_magic_mock()) as mock_compute_hash, \
        mock.patch("builtins.open", MagicMock(side_effect=OSError("error"))), \
        patch.object(HashThePlanet, "find_hash", return_magic_mock()) as mock_htp_find_hash:
        main()

        mock_compute_hash.assert_not_called()
        mock_hash_find_hash.assert_called_once_with("license.txt")

    with mock.patch('sys.argv', ["/foobar/", "--hash", "super_hash"]), \
        patch.object(HashThePlanet, "compute_hashs", return_magic_mock()) as mock_compute_hash, \
        patch.object(HashThePlanet, "find_hash", return_magic_mock()) as mock_htp_find_hash:
        main()

        mock_compute_hash.assert_not_called()
        mock_htp_find_hash.assert_called_once()
        mock_htp_find_hash.assert_called_once_with("super_hash")
