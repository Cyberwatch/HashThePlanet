"""
Unit tests for NpmResource class.
"""
#standard imports
from typing import Dict
from unittest import mock
from unittest.mock import MagicMock, mock_open
import hashlib

# project imports
from hashtheplanet.resources.npm_resource import NpmResource

def test_retrieve_versions():
    """
    Unit tests for retrieve_versions method.
    """
    npm_module_name = "test"

    class MockedPage():
        def __init__(self) -> None:
            self.content = """
            <html>
            <head><title></title></head>
            <body>
                <div id="tabpanel-versions">
                    <div>
                        <div></div>
                        <h3></h3>
                        <ul><li></li></ul>
                        <ul>
                            <li></li>
                            <li><a>1.0.1</a></li>
                            <li><a>1.0.2</a></li>
                            <li><a>1.0.3</a></li>
                        </ul>
                    </div>
                    <div></div>
                </div>
            </body></html>
            """
    def mocked_get_request(url: str, *args, **kwargs):
        assert url == f"https://www.npmjs.com/package/{npm_module_name}?activeTab=versions"
        return MockedPage()

    with mock.patch("requests.get", MagicMock(side_effect=mocked_get_request)):
        npm_resource = NpmResource(MagicMock())

        assert len(npm_resource.retrieve_versions(npm_module_name)) == 3

def test_save_tar_to_disk():
    file_path = "test.tgz"
    npm_module_name = "test"
    version = "1.0.0"

    class MockedPage():
        def __init__(self) -> None:
            self.content = "test content"

    def mocked_get_request(url: str, *args, **kwargs):
        assert url == f"https://registry.npmjs.org/test/-/{npm_module_name}-{version}.tgz"
        return MockedPage()

    with mock.patch("builtins.open", new_callable=mock_open) as io_mock, \
        mock.patch("requests.get", MagicMock(side_effect=mocked_get_request)) as request_mock:
        npm_resource = NpmResource(MagicMock())

        npm_resource.save_tar_to_disk(file_path, npm_module_name, version)
        assert request_mock.called is True
        assert request_mock.call_count == 1
        assert io_mock.called is True
        assert io_mock.call_count == 1

def test_extract_hashes_from_tar():
    path = "./test.tgz"
    members = ["a", "b", None, "c"]

    class MockedTarMember():
        def __init__(self, member) -> None:
            self.path = member

    class MockedTarExtractedFile():
        def __init__(self, member: MockedTarMember) -> None:
            self.member = member

        def read(self):
            return self.member.path.encode("utf-8")

    class MockedTarFile():

        def getmembers(self):
            return [MockedTarMember(member) for member in members]

        def extractfile(self, member: MockedTarMember):
            if member.path is None:
                return None
            return MockedTarExtractedFile(member)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def mocked_open_tar(file_path: str) -> MockedTarFile:
        assert file_path == path
        return MockedTarFile()

    with mock.patch("tarfile.open", MagicMock(side_effect=mocked_open_tar)) as mock_open_tar:
        npm_resource = NpmResource(MagicMock())

        files = npm_resource.extract_hashes_from_tar(path)
        assert mock_open_tar.called is True
        assert mock_open_tar.call_count == 1

        assert len(files) == 3

        assert files[0][0] == "a"
        assert files[0][1] == hashlib.sha256("a".encode("utf-8")).hexdigest()

        assert files[1][0] == "b"
        assert files[1][1] == hashlib.sha256("b".encode("utf-8")).hexdigest()

        assert files[2][0] == "c"
        assert files[2][1] == hashlib.sha256("c".encode("utf-8")).hexdigest()


def test_save_hashes():
    npm_module_name = "test"
    versions = ["1.2.3", "1.2.4"]
    files_info = {
        "1.2.3": [["a.txt", "abc"]],
        "1.2.4": [["b.txt", "123"]]
    }

    class MockDbConnector():

        def __init__(self, session) -> None:
            self.session = session

        def insert_versions(self, session, module_name, module_versions):
            assert module_name == npm_module_name
            assert module_versions == versions

        def insert_file(self, session, module_name, file_path):
            assert module_name == npm_module_name
            assert file_path in (files_info["1.2.3"][0][0], files_info["1.2.4"][0][0])

        def insert_or_update_hash(self, session, file_hash, module_name, versions):
            assert file_hash in (files_info["1.2.3"][0][1], files_info["1.2.4"][0][1])
            assert module_name == npm_module_name
            assert versions in (["1.2.3"], ["1.2.4"])

    session = MagicMock()
    npm_resource = NpmResource(MockDbConnector(session))

    npm_resource._save_hashes(session, files_info, versions, npm_module_name)

def test_compute_hashes():
    versions = ["1.2.3", "1.2.4"]
    target = "test"
    tmp_dir_path = "tmp_dir"
    files_info = {
        "1.2.3": [["a.txt", "abc"]],
        "1.2.4": [["b.txt", "123"]]
    }

    class MockDir():
        def __enter__(self):
            return tmp_dir_path

        def __exit__(self, *args):
            pass

    def mock_tmp_dir():
        return MockDir()

    def mock_extract_hashes_from_tar(file_path: str):
        if file_path == f"{tmp_dir_path}/{target}-1.2.3.tgz":
            return files_info["1.2.3"]
        elif file_path == f"{tmp_dir_path}/{target}-1.2.4.tgz":
            return files_info["1.2.4"]
        return None

    magic_mock_extract = MagicMock(side_effect=mock_extract_hashes_from_tar)

    with mock.patch.object(NpmResource, "retrieve_versions", return_value=versions) as mock_versions, \
        mock.patch.object(NpmResource, "save_tar_to_disk", return_value=None) as mock_tar, \
        mock.patch.object(NpmResource, "extract_hashes_from_tar", magic_mock_extract) as mock_extract, \
        mock.patch.object(NpmResource, "_save_hashes", return_value=None) as mock_save, \
        mock.patch("tempfile.TemporaryDirectory", MagicMock(side_effect=mock_tmp_dir)):
        npm_resource = NpmResource(MagicMock())
        session = MagicMock()
        npm_resource.compute_hashes(session, target)

        mock_versions.assert_called_once()
        mock_tar.call_count == 2
        mock_tar.assert_called_with(f"{tmp_dir_path}/{target}-1.2.4.tgz", 'test', '1.2.4')
        mock_extract.call_count == 2
        mock_save.assert_called_once()
        mock_save.assert_called_with(
            session,
            files_info,
            versions,
            target
        )
