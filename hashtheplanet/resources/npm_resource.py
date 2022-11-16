"""
This module handles npm resources to generate hashes.
"""
#standard imports
import tarfile
import tempfile
from typing import Dict, List, Set, Tuple
import requests

# third party imports
from loguru import logger
from bs4 import BeautifulSoup

# project imports
from hashtheplanet.sql.db_connector import Hash
from hashtheplanet.resources.resource import Resource

# types
FileHash = str
FilePath = str
VersionName = str
FileMetadata = Tuple[FilePath, FileHash]

class NpmResource(Resource):
    """
    This class implements methods to generate hashes from npm resources.
    """
    name = "npm"

    @staticmethod
    def retrieve_versions(npm_module_name: str) -> Set[VersionName]:
        """
        This method retrieves npm module versions.
        """
        page = requests.get(f"https://www.npmjs.com/package/{npm_module_name}?activeTab=versions", timeout=10)
        soup = BeautifulSoup(page.content, "html.parser")
        versions = set()

        table = soup.find('div', attrs={'id':'tabpanel-versions'})

        table_body_version_elements = list(table.find_all())[0]

        version_rows = table_body_version_elements.find_all("li")

        for row in list(version_rows):
            version = row.find("a")
            if version is None:
                continue
            versions.add(version.get_text())
        return versions

    @staticmethod
    def save_tar_to_disk(file_path: str, npm_module_name: str, version: str):
        """
        This method downloads a tar file containing the specific version of an npm module.
        """
        request = requests.get(
            f"https://registry.npmjs.org/{npm_module_name}/-/{npm_module_name}-{version}.tgz",
            allow_redirects=True,
            timeout=10
        )
        with open(file_path, 'wb') as file_fd:
            file_fd.write(request.content)

    @staticmethod
    def extract_hashes_from_tar(file_path: str) -> List[FileMetadata]:
        """
        This method returns all hashes of all files contained in a tar file.
        """
        files = []

        with tarfile.open(file_path) as tar:
            for member in tar.getmembers():
                file = tar.extractfile(member)

                if file is None:
                    continue
                files.append((member.path, Hash.hash_bytes(file.read())))
        return files

    def _save_hashes(
        self,
        session_scope,
        files_info: Dict[VersionName, List[FileMetadata]],
        versions: List[VersionName],
        npm_module_name: str
    ):
        """
        This method saves all files with their hash & their versions to the database.
        """
        with session_scope() as session:
            self._database.insert_versions(session, npm_module_name, versions)
            for version, files in files_info.items():
                for (file_path, file_hash) in files:
                    self._database.insert_file(session, npm_module_name, file_path)
                    self._database.insert_or_update_hash(session, file_hash, npm_module_name, [version])

    def compute_hashes(self, session_scope, target: str):
        """
        This method downloads all versions of an npm module and stores all the versions with their associated files
        and hashes and stores them in the database.
        """
        versions = self.retrieve_versions(target)
        files_info: Dict[VersionName, List[FileMetadata]] = {}

        with tempfile.TemporaryDirectory() as tmp_dir_name:
            for version in versions:
                logger.debug(f"Downloading {target}-v{version} ...")
                file_path = f"{tmp_dir_name}/{target}-{version}.tgz"

                self.save_tar_to_disk(file_path, target, version)
                files_info[version] = self.extract_hashes_from_tar(file_path)

        self._save_hashes(session_scope, files_info, versions, target)
